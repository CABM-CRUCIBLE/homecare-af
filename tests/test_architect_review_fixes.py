# Author: C A B M
# Date: 2026-09-17

"""Tests validating Senior Software Architect Code Review fixes.

Validates:
1. Format specifier fix in CheckpointManager error logging.
2. Atomic write-and-replace in CheckpointManager.
3. Fail-safe architecture review on revision failure.
4. Non-blocking test execution via asyncio.to_thread.
5. Hierarchical git branch head resolution.
6. Safe git remote resolution (non-origin remotes).
7. Nested backticks and markdown code parsing in execute_prompt.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.checkpoint import CheckpointManager
from homecare_agent.graph.main_graph import _revise_architecture, _run_tests
from homecare_agent.graph.nodes.execute_prompt import _parse_generated_files
from homecare_agent.graph.nodes.git_ops import create_branch
from homecare_agent.graph.state import AgentState


# ─── Fix 1 & 5: Checkpoint Logging & Atomic Writes ──────────────────────────


def test_checkpoint_atomic_write_and_logging_format(tmp_path: Path):
    """Verify atomic write-and-replace and error logging specifier."""
    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    state = {"feature_name": "Atomic Test", "completed_steps": ["intake_feature"]}

    # Normal save
    saved = mgr.save_checkpoint("trace_atomic_1", state, last_step="intake_feature")
    assert saved.exists()
    assert not saved.with_suffix(".tmp").exists()

    # Simulate error logging to ensure %s format specifier does not raise TypeError
    with patch("builtins.open", side_effect=PermissionError("Mock write permission denied")), \
         patch("homecare_agent.graph.checkpoint.logger.error") as mock_log_err:
        mgr.save_checkpoint("trace_atomic_err", state, last_step="intake_feature")
        mock_log_err.assert_called_once()
        log_args = mock_log_err.call_args[0]
        # Ensure message has %s format and exception is passed cleanly
        assert "%s: %s" in log_args[0]


# ─── Fix 2: Fail-Safe Architecture Revision ──────────────────────────────────


@pytest.mark.asyncio
async def test_revise_architecture_fails_safe_on_llm_exception():
    """Verify that an exception in architecture revision sets architecture_approved to False."""
    settings = Settings(openrouter_api_key="test-key", repo_path=".")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("OpenRouter 503 Service Unavailable"))

    state: AgentState = {
        "trace_id": "test_trace_rev_err",
        "feature_name": "Caregiver Triage",
        "architecture_review": "CRITICAL FINDING: Missing tenant isolation in queries.",
        "arch_iteration": 1,
    }

    result = await _revise_architecture(state, settings=settings, llm=mock_llm)

    # CRITICAL: Must be False to prevent unverified architecture from progressing!
    assert result["architecture_approved"] is False
    assert result["arch_iteration"] == 2
    assert len(result.get("errors", [])) == 1


# ─── Fix 3 & 7: Non-Blocking Test Execution & Dynamic Paths ──────────────────


@pytest.mark.asyncio
async def test_run_tests_uses_asyncio_to_thread(tmp_path: Path):
    """Verify _run_tests offloads subprocess.run to worker threads via asyncio.to_thread."""
    settings = Settings(repo_path=str(tmp_path))
    state: AgentState = {"trace_id": "test_non_blocking", "feature_name": "Test Feature"}

    # Mock asyncio.to_thread
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        mock_proc = MagicMock(returncode=0, stdout="Passed: 10, Failed: 0")
        mock_to_thread.return_value = mock_proc

        # Create dummy backend sln to trigger discovery
        backend_dir = tmp_path / "src" / "Backend"
        backend_dir.mkdir(parents=True)
        (backend_dir / "HomeCare.sln").touch()

        result = await _run_tests(state, settings=settings, test_type="unit")

        assert result["unit_test_results"]["type"] == "unit"
        # asyncio.to_thread was called for subprocess.run
        assert mock_to_thread.called


# ─── Fix 4 & 8: Git Branch Resolution & Safe Remotes ─────────────────────────


@pytest.mark.asyncio
async def test_git_branch_hierarchical_resolution_and_remote_safety():
    """Verify hierarchical branch checkout and safe remote fallback."""
    settings = Settings(repo_path=".", repo_default_branch="main")
    state: AgentState = {
        "trace_id": "test_git_trace",
        "feature_name": "Order Fulfillment",
    }

    with patch("git.Repo") as MockRepo:
        repo_inst = MockRepo.return_value

        # Mock remote named 'upstream' (no 'origin')
        mock_upstream = MagicMock()
        mock_upstream.name = "upstream"
        repo_inst.remotes = [mock_upstream]

        # Existing head has hierarchical name "feature/order-fulfillment"
        head_branch = MagicMock()
        head_branch.name = "feature/order-fulfillment"
        default_head = MagicMock()
        default_head.name = "main"

        repo_inst.heads = {
            "main": default_head,
            "feature/order-fulfillment": head_branch,
        }

        result = await create_branch(state, settings)

        assert result["branch_name"] == "feature/order-fulfillment"
        # Existing head was checked out rather than trying to recreate
        head_branch.checkout.assert_called_once()
        # Fallback remote 'upstream' was used to push
        mock_upstream.push.assert_called_once()


# ─── Fix 6: Nested Backtick & Markdown Parsing in Code Generation ────────────


def test_parse_generated_files_preserves_nested_backticks():
    """Verify parser does not truncate when file contains nested backticks or markdown fences."""
    sample_llm_response = '''
Here are the generated files for your work package:

### FILE: src/docs/README.md
```markdown
# Documentation
Here is an example of code:
```csharp
var client = new HttpClient();
```
End of documentation.
```

### FILE: src/Services/OrderService.cs
```csharp
namespace HomeCare.Services;

public class OrderService
{
    // String with `inline backticks`
    public string Description => "Order service with `code` comments";
}
```
'''

    parsed = _parse_generated_files(sample_llm_response)

    assert "src/docs/README.md" in parsed
    assert "src/Services/OrderService.cs" in parsed

    readme_content = parsed["src/docs/README.md"]
    # Internal code fence was preserved and not prematurely truncated
    assert "```csharp" in readme_content
    assert 'var client = new HttpClient();' in readme_content
    assert "End of documentation." in readme_content

    cs_content = parsed["src/Services/OrderService.cs"]
    assert "public class OrderService" in cs_content
    assert "`inline backticks`" in cs_content


# ─── Fix 7: Git commit before push (B-02) ───────────────────────────────────


@pytest.mark.asyncio
async def test_commit_and_push_calls_index_commit(tmp_path: Path):
    """Verify commit_and_push calls repo.index.commit before pushing to remote."""
    from homecare_agent.graph.nodes.git_ops import commit_and_push

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    file_path = repo_dir / "src" / "Service.cs"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("// safe code", encoding="utf-8")

    state = {
        "repo_path": str(repo_dir),
        "branch_name": "feature/test-branch",
        "trace_id": "0123456789abcdef0123456789abcdef",
    }
    settings = Settings(openrouter_api_key="sk-test", repo_path=str(repo_dir))

    mock_repo = MagicMock()
    mock_repo.index.diff.return_value = []
    mock_repo.untracked_files = ["src/Service.cs"]

    mock_remote = MagicMock()
    mock_remote.name = "origin"
    mock_repo.remotes = [mock_remote]

    with patch("git.Repo", return_value=mock_repo), \
         patch("homecare_agent.graph.nodes.git_ops.scan_file_for_secrets", return_value=[]):
        result = await commit_and_push(state, settings, message="feat: added Service", step_name="step_test")

    mock_repo.git.add.assert_called_once_with(["src/Service.cs"])
    mock_repo.index.commit.assert_called_once_with("feat: added Service")
    mock_remote.push.assert_called_once_with("feature/test-branch")
    assert result["current_step"] == "step_test"


# ─── Fix 8: SHA-256 Trace ID Normalization (Md-02) ──────────────────────────


def test_normalize_trace_id_sha256():
    """Verify non-standard trace IDs are normalized to 32-char hex via SHA-256."""
    from homecare_agent.llm.provider import normalize_trace_id
    import hashlib

    custom_id = "homecare-workflow-feature-12345-long-slug"
    cleaned = custom_id.replace("-", "").strip().lower()
    norm = normalize_trace_id(custom_id)
    assert len(norm) == 32
    assert norm == hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:32]


# ─── Fix 9: File Tools delete_file Sandboxing (Md-01) ────────────────────────


def test_delete_file_sandboxed(tmp_path: Path):
    """Verify delete_file respects sandboxing and deletes within base directory."""
    from homecare_agent.tools.file_tools import delete_file, PathTraversalSecurityError

    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    target = sandbox / "test.txt"
    target.write_text("hello", encoding="utf-8")

    assert target.exists()
    assert delete_file("test.txt", base_dir=sandbox) is True
    assert not target.exists()

    with pytest.raises(PathTraversalSecurityError):
        delete_file("../outside.txt", base_dir=sandbox)


# ─── Fix 10: State Tracking for Written Files (M-04) ─────────────────────────


@pytest.mark.asyncio
async def test_write_generated_files_returns_written_files_list(tmp_path: Path):
    """Verify write_generated_files tracks and returns written_files in state."""
    from homecare_agent.graph.nodes.execute_prompt import write_generated_files

    state = {
        "repo_path": str(tmp_path),
        "feature_name": "Test Feature",
        "generated_code": {
            "src/models/User.cs": "namespace HomeCare; public class User {}",
            "src/models/Order.cs": "namespace HomeCare; public class Order {}",
        },
    }
    settings = Settings(openrouter_api_key="sk-test", repo_path=str(tmp_path))

    result = await write_generated_files(state, settings)
    assert "written_files" in result
    assert "src/models/User.cs" in result["written_files"]
    assert "src/models/Order.cs" in result["written_files"]
    assert (tmp_path / "src" / "models" / "User.cs").exists()
