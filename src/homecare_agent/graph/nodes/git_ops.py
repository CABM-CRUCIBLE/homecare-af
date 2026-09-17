# Author: C A B M
# Date: 2026-09-17

"""Git operations node.

Handles branch creation, staging, committing, pushing, and PR creation.
Supports both GitHub PAT and GitHub App authentication.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from homecare_agent.config import AuthMode, Settings
from homecare_agent.graph.state import AgentState

logger = logging.getLogger(__name__)


class GitSecurityViolationError(Exception):
    """Raised when sensitive files or secrets are detected during git operations."""

    pass


SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Cryptographic Private Key"),
    (re.compile(r"sk-or-v1-[a-f0-9]{64}"), "OpenRouter API Key"),
    (re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"), "Anthropic API Key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{82}"), "GitHub Fine-Grained Token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key"),
]

FORBIDDEN_STAGING_PATTERNS = [
    ".env",
    ".pem",
    ".key",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
]


def scan_file_for_secrets(file_path: Path) -> list[str]:
    """Scan a file for known API keys, private keys, or credentials."""
    findings = []
    try:
        if file_path.stat().st_size > 1_000_000:
            return findings
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(label)
    except Exception:
        pass
    return findings


def is_forbidden_staging_file(file_name: str) -> bool:
    """Check if file matches forbidden staging list."""
    lower = file_name.lower().replace("\\", "/")
    return any(pat in lower for pat in FORBIDDEN_STAGING_PATTERNS)


async def create_branch(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Create a feature branch and push to origin.

    Branch naming: feature/<module-name-kebab-case>

    Returns:
        State updates with branch_name.
    """
    from git import Repo

    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "feature")
    # Convert to kebab-case
    branch_name = "feature/" + re.sub(r"[^a-z0-9]+", "-", feature_name.lower()).strip("-")

    repo_path = state.get("repo_path", settings.repo_path)
    logger.info(
        "[START:create_branch][trace_id=%s] Creating branch '%s' for '%s' at %s",
        trace_id,
        branch_name,
        feature_name,
        repo_path,
    )

    try:
        repo = Repo(repo_path)

        # Safely resolve remote (don't assume remote is named 'origin')
        target_remote = None
        if repo.remotes:
            target_remote = repo.remotes.origin if "origin" in [r.name for r in repo.remotes] else repo.remotes[0]

        # Collect existing head names safely whether heads is IterableList or dict
        existing_heads = [ref if isinstance(ref, str) else getattr(ref, "name", str(ref)) for ref in repo.heads]

        # Ensure we're on the latest default branch
        default_branch = settings.repo_default_branch
        if default_branch in existing_heads:
            repo.heads[default_branch].checkout()  # type: ignore[index]
            if target_remote:
                try:
                    target_remote.pull()
                except Exception as pull_err:
                    logger.warning("[create_branch][trace_id=%s] Pull from remote skipped or failed: %s", trace_id, pull_err)

        # Create and checkout new branch (supports full hierarchical name and short name)
        short_name = branch_name.split("/")[-1]

        if branch_name in existing_heads:
            logger.info("[create_branch][trace_id=%s] Branch '%s' already exists; checking out.", trace_id, branch_name)
            repo.heads[branch_name].checkout()  # type: ignore[index]
        elif short_name in existing_heads:
            logger.info("[create_branch][trace_id=%s] Branch '%s' already exists; checking out.", trace_id, short_name)
            repo.heads[short_name].checkout()  # type: ignore[index]
        else:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()

        # Persist architecture documents and visual resources immediately (ARCH-PERSIST)
        from homecare_agent.graph.nodes.documentation import (
            get_feature_docs_dir,
            save_architecture_documents,
        )

        arch_files = save_architecture_documents(state, settings)
        if arch_files:
            try:
                repo.git.add(arch_files)
                commit_msg = f"docs(architecture): add strategy, tactical plan, ADRs, and visual resources for {feature_name}"
                repo.index.commit(commit_msg)
                logger.info(
                    "[create_branch][trace_id=%s] Committed %d architecture file(s) on branch '%s'",
                    trace_id,
                    len(arch_files),
                    branch_name,
                )
            except Exception as commit_err:
                logger.warning("[create_branch][trace_id=%s] Architecture commit note: %s", trace_id, commit_err)

        # Push to remote (pushes branch and initial architecture commit)
        if target_remote:
            try:
                target_remote.push(branch_name, set_upstream=True)
                logger.info("[create_branch][trace_id=%s] Branch pushed to remote: %s", trace_id, branch_name)
            except Exception as push_err:
                logger.warning("[create_branch][trace_id=%s] Remote push skipped or failed: %s", trace_id, push_err)

        arch_dir_rel = str(get_feature_docs_dir(repo_path, feature_name).relative_to(Path(repo_path))).replace("\\", "/")

        logger.info(
            "[COMPLETED:create_branch][trace_id=%s] Branch '%s' successfully checked out with %d architecture doc(s) in %s",
            trace_id,
            branch_name,
            len(arch_files),
            arch_dir_rel,
        )

        return {
            "branch_name": branch_name,
            "arch_docs_dir": arch_dir_rel,
            "written_arch_files": arch_files,
            "current_step": "create_branch",
            "completed_steps": ["create_branch"],
        }

    except Exception as e:
        logger.error(
            "[ERROR:create_branch][trace_id=%s] Branch creation failed for '%s' (branch: %s): %s",
            trace_id,
            feature_name,
            branch_name,
            e,
            exc_info=True,
        )
        return {
            "branch_name": branch_name,
            "errors": [{"step": "create_branch", "trace_id": trace_id, "message": f"Branch creation failed: {e}"}],
            "current_step": "create_branch",
            "completed_steps": ["create_branch"],
        }


async def commit_and_push(
    state: AgentState,
    settings: Settings,
    message: str = "",
    step_name: str = "commit",
) -> dict[str, Any]:
    """Stage all changes, commit, and push.

    Args:
        state: Current graph state.
        settings: Application settings.
        message: Commit message.
        step_name: Name of this step for tracking.

    Returns:
        State updates with commit log entry.
    """
    from git import Repo

    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "feature")
    repo_path = state.get("repo_path", settings.repo_path)
    branch_name = state.get("branch_name", "")

    if not message:
        message = f"feat({feature_name}): {step_name}"

    logger.info(
        "[START:commit_and_push][trace_id=%s] Staging, committing, and pushing step '%s' on branch '%s'",
        trace_id,
        step_name,
        branch_name,
    )

    try:
        repo = Repo(repo_path)

        # Collect changed & untracked files
        changed = [item.a_path for item in repo.index.diff(None)]
        untracked = list(repo.untracked_files)
        candidates = sorted(set(changed + untracked))

        safe_to_stage: list[str] = []
        for file_rel in candidates:
            if is_forbidden_staging_file(file_rel):
                logger.critical(
                    "[CRITICAL:commit_and_push][trace_id=%s] Staging aborted: forbidden sensitive file detected: %s",
                    trace_id,
                    file_rel,
                )
                raise GitSecurityViolationError(
                    f"Forbidden file pattern '{file_rel}' blocked from git staging."
                )

            full_p = Path(repo_path) / file_rel
            if full_p.exists() and full_p.is_file():
                secrets = scan_file_for_secrets(full_p)
                if secrets:
                    logger.critical(
                        "[CRITICAL:commit_and_push][trace_id=%s] Staging aborted: secret (%s) detected in file %s",
                        trace_id,
                        ", ".join(secrets),
                        file_rel,
                    )
                    raise GitSecurityViolationError(
                        f"Secret detected in '{file_rel}' ({', '.join(secrets)}). Staging halted."
                    )
                safe_to_stage.append(file_rel)

        if safe_to_stage:
            repo.git.add(safe_to_stage)
            try:
                repo.index.commit(message)
                if repo.remotes and branch_name:
                    remote = next((r for r in repo.remotes if getattr(r, "name", "") == "origin"), repo.remotes[0])
                    try:
                        remote.push(branch_name)
                    except Exception as push_err:
                        logger.warning("[commit_and_push][trace_id=%s] Remote push skipped or failed: %s", trace_id, push_err)
                logger.info("[COMPLETED:commit_and_push][trace_id=%s] Committed and pushed %d file(s): %s", trace_id, len(safe_to_stage), message)
            except Exception as commit_err:
                logger.warning("[commit_and_push][trace_id=%s] Commit skipped or clean: %s", trace_id, commit_err)
        else:
            logger.info("[COMPLETED:commit_and_push][trace_id=%s] No changes to commit for step '%s'.", trace_id, step_name)

        return {
            "commit_log": [{"step": step_name, "message": message}],
            "current_step": step_name,
            "completed_steps": [step_name],
        }

    except Exception as e:
        logger.error(
            "[ERROR:commit_and_push][trace_id=%s] Commit/push failed for step '%s': %s",
            trace_id,
            step_name,
            e,
            exc_info=True,
        )
        return {
            "errors": [{"step": step_name, "trace_id": trace_id, "message": f"Commit/push failed: {e}"}],
            "current_step": step_name,
            "completed_steps": [step_name],
        }


async def create_pull_request(state: AgentState, settings: Settings, llm: Any = None) -> dict[str, Any]:
    """Create a GitHub Pull Request.

    Creates a PR with a detailed description including:
    - Feature summary
    - Files changed
    - Test results
    - Architecture decisions referenced

    Returns:
        State updates with PR number and URL.
    """
    trace_id = state.get("trace_id", "no-trace")
    branch_name = state.get("branch_name", "")
    feature_name = state.get("feature_name", "")

    logger.info(
        "[START:create_pull_request][trace_id=%s] Creating Pull Request for '%s' from branch '%s'...",
        trace_id,
        feature_name,
        branch_name,
    )

    # Build PR description
    pr_body = f"""## Feature: {feature_name}

### Summary
{state.get("feature_description", "")}

### Architecture Documents
- Strategy Document
- Tactical Plan
- {len(state.get("adr_documents", []))} ADR(s)

### Changes
- {len(state.get("generated_code", {}))} files generated/modified
- Organized into {state.get("current_wave", 0)} wave(s)

### Test Results
- Backend: {_summarize_test(state.get("backend_test_results", {}))}
- Frontend: {_summarize_test(state.get("frontend_test_results", {}))}
- E2E: {_summarize_test(state.get("e2e_test_results", {}))}

### Code Review
- Iterations: {state.get("review_iteration", 0)}
- Status: {"Approved" if not state.get("review_changes_needed") else "Changes Requested"}
"""

    try:
        from github import Github, Auth

        if settings.github_auth_mode == AuthMode.PAT:
            gh = Github(auth=Auth.Token(settings.github_token))
        else:
            from github import GithubIntegration
            integration = GithubIntegration(
                integration_id=settings.github_app_id,
                private_key=Path(settings.github_app_private_key_path).read_text(encoding="utf-8"),
            )
            installation = integration.get_installations()[0]
            gh = installation.get_github_for_installation()

        # Extract owner/repo from URL
        repo_url = state.get("repo_url", settings.repo_url)
        repo_match = re.search(r"github\.com[:/](.+/.+?)(?:\.git)?$", repo_url)
        if not repo_match:
            raise ValueError(f"Could not parse repo from URL: {repo_url}")

        repo = gh.get_repo(repo_match.group(1))
        pr = repo.create_pull(
            title=f"feat: {feature_name}",
            body=pr_body,
            head=branch_name,
            base=settings.repo_default_branch,
        )

        logger.info(
            "[COMPLETED:create_pull_request][trace_id=%s] PR created: #%d — %s",
            trace_id,
            pr.number,
            pr.html_url,
        )

        return {
            "pr_number": pr.number,
            "pr_url": pr.html_url,
            "current_step": "create_pr",
            "completed_steps": ["create_pr"],
        }

    except Exception as e:
        logger.error(
            "[ERROR:create_pull_request][trace_id=%s] PR creation failed for '%s': %s",
            trace_id,
            feature_name,
            e,
            exc_info=True,
        )
        return {
            "errors": [{"step": "create_pr", "trace_id": trace_id, "message": f"PR creation failed: {e}"}],
            "current_step": "create_pr",
            "completed_steps": ["create_pr"],
        }


def _summarize_test(results: dict[str, Any]) -> str:
    """Summarize test results into a brief string."""
    if not results:
        return "Not run"
    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    total = results.get("total", passed + failed)
    status = "✅ Pass" if failed == 0 else "❌ Fail"
    return f"{status} ({passed}/{total})"
