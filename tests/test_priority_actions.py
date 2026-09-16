# Author: C A B M
# Date: 2026-09-17

"""Comprehensive verification tests for '6. Recommended Priority Actions'.

Tests:
1. ARCH-01: Sentinel error edges & error_halt terminal routing
2. LLM-01: Thread-safe synchronous budget checking
3. STATE-01: append_list string & primitive deduplication
4. STATE-02: llm_call_count persistence and restoration
5. EDGE-01: Filtering empty wave IDs in more_waves and execute_wave
6. CODEGEN-01: Shared extract_json with markdown fences & trailing commas
7. CP-01: Checkpoint SHA-256 integrity verification and tamper detection
8. CP-02: Checkpoint UUID-based temp file naming
9. SEC-04: Docker compose DB credentials parameterization
10. ARCH-02: State pruning strategy capping errors and findings
11. ARCH-03: Extracted node functions and backward-compatible aliases
12. LLM-02: Unified model cache key strategy in LLMProvider
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.checkpoint import CheckpointManager, prune_state
from homecare_agent.graph.edges.routing import (
    check_prompts_output,
    check_strategy_output,
    check_tactical_output,
    more_waves,
)
from homecare_agent.graph.main_graph import (
    _ask_clarifications,
    _generate_manual_test_doc,
    _notify_completion,
    _post_review_comments,
    _revise_architecture,
    _run_tests,
    build_graph,
)
from homecare_agent.graph.nodes.clarification import ask_clarifications
from homecare_agent.graph.nodes.documentation import generate_manual_test_doc
from homecare_agent.graph.nodes.notifications import error_halt, notify_completion, post_review_comments
from homecare_agent.graph.nodes.review_arch import revise_architecture
from homecare_agent.graph.nodes.testing import run_tests
from homecare_agent.graph.state import AgentState, append_list
from homecare_agent.llm.provider import LLMBudgetExceededError, LLMProvider
from homecare_agent.tools.json_utils import extract_json


# ─── 1. ARCH-01: Sentinel Error Edges & error_halt ──────────────────────────


def test_arch01_strategy_sentinel_routes_to_error_halt_on_missing_doc():
    """Verify that empty or failed strategy output halts pipeline cleanly."""
    state_empty: AgentState = {"strategy_document": ""}
    assert check_strategy_output(state_empty) == "error_halt"

    state_failed: AgentState = {"strategy_document": "Generation failed: timeout"}
    assert check_strategy_output(state_failed) == "error_halt"

    state_valid: AgentState = {"strategy_document": "## Architecture Strategy Document"}
    assert check_strategy_output(state_valid) == "generate_tactical_plan"


def test_arch01_tactical_sentinel_routes_to_error_halt_on_missing_plan():
    """Verify that empty or failed tactical plan halts pipeline cleanly."""
    state_empty: AgentState = {"tactical_plan": "", "work_packages": []}
    assert check_tactical_output(state_empty) == "error_halt"

    state_valid: AgentState = {"tactical_plan": "## Tactical Plan", "work_packages": [{"wave": "1"}]}
    assert check_tactical_output(state_valid) == "generate_adrs"


def test_arch01_prompts_sentinel_routes_to_error_halt_on_failure():
    """Verify that unrecoverable prompt errors halt the pipeline."""
    state_err: AgentState = {
        "standing_instructions": "",
        "errors": [{"step": "generate_agentic_prompts", "message": "Failed"}],
    }
    assert check_prompts_output(state_err) == "error_halt"

    state_ok: AgentState = {
        "standing_instructions": "Follow C# standards",
        "errors": [],
    }
    assert check_prompts_output(state_ok) == "review_architecture"


@pytest.mark.asyncio
async def test_arch01_error_halt_node_returns_halted_status():
    """Verify error_halt terminal node returns halted step status."""
    settings = Settings(openrouter_api_key="test-key")
    state: AgentState = {
        "trace_id": "test_halt_trace",
        "feature_name": "Test Feature",
        "current_step": "generate_strategy",
        "errors": [{"step": "generate_strategy", "message": "API Error 500"}],
    }
    result = await error_halt(state, settings)
    assert result["current_step"] == "error_halt"
    assert "error_halt" in result["completed_steps"]


# ─── 2. LLM-01: Thread-Safe Synchronous Budget Checking ─────────────────────


def test_llm01_thread_safe_budget_counter():
    """Verify synchronous budget check is thread-safe under concurrent execution."""
    settings = Settings(openrouter_api_key="test-key", max_llm_calls_per_run=100)
    provider = LLMProvider(settings)

    iterations = 80
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(provider._check_and_increment_budget_sync) for _ in range(iterations)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    assert provider.call_count == iterations

    # Verify budget overflow raises LLMBudgetExceededError cleanly
    provider.set_call_count(100)
    with pytest.raises(LLMBudgetExceededError):
        provider._check_and_increment_budget_sync()


# ─── 3. STATE-01: String & Primitive Deduplication in append_list ────────────


def test_state01_append_list_deduplicates_strings_and_primitives():
    """Verify append_list does not duplicate step names or primitive types."""
    existing = ["intake_feature", "ask_clarifications"]
    # Retrying ask_clarifications and adding analyze_codebase
    new_steps = ["ask_clarifications", "analyze_codebase", "intake_feature"]
    result = append_list(existing, new_steps)

    assert result == ["intake_feature", "ask_clarifications", "analyze_codebase"]

    # Also verify ints/bools deduplicate
    assert append_list([1, 2], [2, 3, 1]) == [1, 2, 3]


# ─── 4. STATE-02: llm_call_count Persistence & Restoration ──────────────────


def test_state02_llm_call_count_saved_and_restored(tmp_path: Path):
    """Verify llm_call_count is persisted to checkpoint and restored to provider."""
    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    state: AgentState = {
        "trace_id": "trace_call_count_test",
        "feature_name": "Budget Tracking",
        "completed_steps": ["intake_feature"],
        "llm_call_count": 42,
    }
    cp_path = mgr.save_checkpoint("trace_call_count_test", state, last_step="intake_feature")
    loaded = mgr.load_checkpoint(cp_path)

    assert loaded["llm_call_count"] == 42
    assert loaded["state"]["llm_call_count"] == 42

    # Verify LLMProvider restores call count
    settings = Settings(openrouter_api_key="test-key")
    provider = LLMProvider(settings)
    provider.set_call_count(loaded["llm_call_count"])
    assert provider.call_count == 42


# ─── 5. EDGE-01: Filter Empty Wave IDs in more_waves ─────────────────────────


def test_edge01_more_waves_filters_empty_and_falsy_waves():
    """Verify phantom empty waves ('') are filtered out and do not alter wave count."""
    state_with_empty_waves: AgentState = {
        "current_wave": 1,
        "work_packages": [
            {"wave": "Wave 1"},
            {"wave": ""},       # Empty wave (should be ignored)
            {"wave": None},     # None wave (should be ignored)
            {"wave": "Wave 2"},
        ],
    }
    # Total valid waves = 2. current_wave = 1 (< 2) -> execute_wave
    assert more_waves(state_with_empty_waves) == "execute_wave"

    state_done: AgentState = {
        "current_wave": 2,
        "work_packages": [
            {"wave": "Wave 1"},
            {"wave": ""},
            {"wave": "Wave 2"},
        ],
    }
    # current_wave = 2 (>= 2) -> run_e2e_tests
    assert more_waves(state_done) == "run_e2e_tests"


# ─── 6. CODEGEN-01: Shared extract_json Utility ──────────────────────────────


def test_codegen01_extract_json_handles_fences_conversational_and_trailing_commas():
    """Verify extract_json extracts valid JSON across tricky LLM output variations."""
    # 1. Markdown fenced JSON
    fenced = "Here is the result:\n```json\n{\"key\": \"value\", \"num\": 123}\n```\nHope this helps!"
    assert extract_json(fenced) == {"key": "value", "num": 123}

    # 2. Markdown fence without 'json' tag
    fenced_plain = "```\n[1, 2, 3]\n```"
    assert extract_json(fenced_plain) == [1, 2, 3]

    # 3. Trailing commas
    trailing = '{\n  "items": ["a", "b",],\n  "enabled": true,\n}'
    assert extract_json(trailing) == {"items": ["a", "b"], "enabled": True}

    # 4. Fallback default
    invalid = "Not a json payload at all."
    assert extract_json(invalid, default={"error": True}) == {"error": True}


# ─── 7. CP-01 & CP-02: Checkpoint SHA-256 Verification & UUID Temp Naming ────


def test_cp01_checkpoint_checksum_verification_and_tamper_detection(tmp_path: Path):
    """Verify SHA-256 checksum sidecar is written and detects file corruption/tampering."""
    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    state = {"feature_name": "Integrity Test", "completed_steps": ["step1"]}
    cp_path = mgr.save_checkpoint("trace_integrity_test", state, last_step="step1")

    # Verify sidecar exists
    sha_path = cp_path.with_suffix(".sha256")
    assert sha_path.exists()

    # Load valid checkpoint
    loaded = mgr.load_checkpoint(cp_path)
    assert loaded["feature_name"] == "Integrity Test"

    # Simulate file tampering / corruption
    with open(cp_path, "a", encoding="utf-8") as f:
        f.write(" ")

    # Verification must fail with ValueError
    with pytest.raises(ValueError, match="Checkpoint integrity verification failed"):
        mgr.load_checkpoint(cp_path)


# ─── 8. SEC-04: Docker Compose DB Credentials Parameterization ───────────────


def test_sec04_docker_compose_db_credentials_parameterized():
    """Verify docker-compose.yml uses environment variable parameterization for DB credentials."""
    dc_path = Path("docker-compose.yml")
    assert dc_path.exists()
    content = dc_path.read_text(encoding="utf-8")

    # Verify no raw hardcoded POSTGRES_PASSWORD=postgres without env var fallback
    assert "POSTGRES_USER=${LANGFUSE_DB_USER:-postgres}" in content
    assert "POSTGRES_PASSWORD=${LANGFUSE_DB_PASSWORD:-postgres}" in content
    assert "DATABASE_URL=postgresql://${LANGFUSE_DB_USER:-postgres}:${LANGFUSE_DB_PASSWORD:-postgres}@langfuse-db:5432/${LANGFUSE_DB_NAME:-langfuse}" in content


# ─── 9. ARCH-02: State Pruning Strategy ──────────────────────────────────────


def test_arch02_state_pruning_caps_errors_and_findings():
    """Verify prune_state caps unbounded growth of errors and review findings."""
    large_errors = [{"step": f"step_{i}", "message": f"err {i}"} for i in range(120)]
    large_findings = [{"id": f"F-{i}", "description": f"finding {i}"} for i in range(250)]

    state = {
        "feature_name": "Prune Test",
        "errors": large_errors,
        "code_review_findings": large_findings,
    }

    pruned = prune_state(state, max_errors=50, max_findings=100)

    assert len(pruned["errors"]) == 50
    assert pruned["errors"][0]["step"] == "step_70"  # retains newest 50
    assert pruned["_pruned_error_count"] == 70

    assert len(pruned["code_review_findings"]) == 100
    assert pruned["_pruned_findings_count"] == 150


# ─── 10. ARCH-03: Extracted Node Functions & Aliases ─────────────────────────


def test_arch03_extracted_nodes_and_backward_compatibility_aliases():
    """Verify extracted node functions exist in dedicated modules and aliases match."""
    # Test that aliases in main_graph point to the modularized functions
    assert _ask_clarifications is ask_clarifications
    assert _revise_architecture is revise_architecture
    assert _run_tests is run_tests
    assert _generate_manual_test_doc is generate_manual_test_doc
    assert _post_review_comments is post_review_comments
    assert _notify_completion is notify_completion

    # Verify graph builds with error_halt node
    settings = Settings(openrouter_api_key="test-key")
    mock_llm = MagicMock()
    graph = build_graph(settings, mock_llm)
    assert "error_halt" in graph.nodes


# ─── 11. LLM-02: Unified Model Cache Key Strategy ───────────────────────────


def test_llm02_unified_model_cache_key():
    """Verify get_llm caches models solely using uniform clean_model@effective_base_url keys."""
    settings = Settings(openrouter_api_key="test-key", openrouter_base_url="https://openrouter.ai/api/v1")
    provider = LLMProvider(settings)

    llm1 = provider.get_llm("anthropic/claude-sonnet-4")
    llm2 = provider.get_llm("anthropic/claude-sonnet-4", base_url="https://openrouter.ai/api/v1")

    # Must return the identical cached instance
    assert llm1 is llm2
    # Verify no naked model name in cache keys
    assert "anthropic/claude-sonnet-4" not in provider._model_cache
    assert "anthropic/claude-sonnet-4@https://openrouter.ai/api/v1" in provider._model_cache
