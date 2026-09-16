# Author: C A B M
# Date: 2026-09-17

"""Tests for State Checkpointing and Resuming Execution from Step 4 or arbitrary steps."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from homecare_agent.config import Settings
from homecare_agent.graph.checkpoint import (
    CheckpointManager,
    ORDERED_STEPS,
    get_step_number,
    resolve_next_step,
    resolve_step_name,
)
from homecare_agent.graph.main_graph import build_graph, compile_graph
from homecare_agent.graph.state import AgentState
from homecare_agent.main import app

runner = CliRunner()


# ─── Step Resolution Tests ───────────────────────────────────────────────────


def test_step_resolution_by_number_and_name():
    """Verify bi-directional mapping between step numbers and canonical node names."""
    # Step 1: intake_feature
    assert resolve_step_name(1) == "intake_feature"
    assert resolve_step_name("1") == "intake_feature"
    assert get_step_number("intake_feature") == 1

    # Step 3: analyze_codebase
    assert resolve_step_name(3) == "analyze_codebase"
    assert resolve_step_name("analyze_codebase") == "analyze_codebase"
    assert get_step_number("analyze_codebase") == 3

    # Step 4: generate_strategy
    assert resolve_step_name(4) == "generate_strategy"
    assert resolve_step_name("4") == "generate_strategy"
    assert resolve_step_name("generate_strategy") == "generate_strategy"
    assert resolve_step_name("generate-strategy") == "generate_strategy"
    assert get_step_number("generate_strategy") == 4

    # Step 14: notify_ready_for_merge
    assert resolve_step_name(14) == "notify_ready_for_merge"
    assert get_step_number("notify_ready_for_merge") == 14

    # Invalid step specifications
    with pytest.raises(ValueError, match="Invalid step number"):
        resolve_step_name(99)

    with pytest.raises(ValueError, match="Unknown step name"):
        resolve_step_name("non_existent_node_xyz")


def test_resolve_next_step_after_step_3_failure():
    """Verify that when execution stops after Step 3, the next step resolves to Step 4."""
    # Simulating a state where step 1 and step 3 completed, then agent stopped
    state: dict = {
        "completed_steps": ["intake_feature", "analyze_codebase"],
        "feature_name": "Test Feature",
    }
    next_step = resolve_next_step(state)
    assert next_step == "generate_strategy"
    assert get_step_number(next_step) == 4


def test_resolve_next_step_explicit_override():
    """Verify explicit step override takes precedence."""
    state: dict = {
        "completed_steps": ["intake_feature", "analyze_codebase"],
    }
    # Explicitly asking for Step 6 (generate_adrs)
    assert resolve_next_step(state, explicit_step=6) == "generate_adrs"
    assert resolve_next_step(state, explicit_step="generate_tactical_plan") == "generate_tactical_plan"


# ─── Checkpoint Manager Tests ────────────────────────────────────────────────


def test_checkpoint_save_and_load(tmp_path: Path):
    """Verify saving and loading state checkpoint preserving complex data."""
    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    trace_id = "test_trace_1234567890abcdef"

    initial_state = {
        "trace_id": trace_id,
        "feature_name": "Caregiver Scheduling",
        "feature_description": "Auto-assign caregivers based on proximity",
        "codebase_analysis": {"existing_models": ["User", "Caregiver"], "total_files": 42},
        "completed_steps": ["intake_feature", "analyze_codebase"],
        "current_step": "analyze_codebase",
    }

    saved_path = mgr.save_checkpoint(trace_id, initial_state, last_step="analyze_codebase")
    assert saved_path.exists()

    loaded = mgr.load_checkpoint(trace_id)
    assert loaded["trace_id"] == trace_id
    assert loaded["feature_name"] == "Caregiver Scheduling"
    assert loaded["last_completed_step"] == "analyze_codebase"
    assert loaded["last_completed_step_number"] == 3

    restored_state = loaded["state"]
    assert restored_state["codebase_analysis"]["total_files"] == 42
    assert "analyze_codebase" in restored_state["completed_steps"]


def test_checkpoint_listing_and_latest(tmp_path: Path):
    """Verify listing checkpoints and retrieving the latest checkpoint."""
    mgr = CheckpointManager(checkpoint_dir=tmp_path)

    # Save run 1
    import time
    state1 = {"feature_name": "Run 1", "completed_steps": ["intake_feature"]}
    mgr.save_checkpoint("trace_run_1", state1, last_step="intake_feature")

    time.sleep(0.05)

    # Save run 2
    state2 = {"feature_name": "Run 2", "completed_steps": ["intake_feature", "analyze_codebase"]}
    mgr.save_checkpoint("trace_run_2", state2, last_step="analyze_codebase")

    checkpoints = mgr.list_checkpoints()
    assert len(checkpoints) == 2

    # Latest should be run 2
    latest = mgr.get_latest_checkpoint()
    assert latest is not None
    assert latest["trace_id"] == "trace_run_2"
    assert latest["last_completed_step"] == "analyze_codebase"


# ─── LangGraph Resumption Tests (Starting from Step 4) ───────────────────────


@pytest.mark.asyncio
async def test_langgraph_resumes_directly_from_step_4():
    """Verify that setting resume_from_step routes directly to Step 4 and skips prior steps."""
    settings = Settings(openrouter_api_key="test-key", repo_path=".")
    mock_llm = MagicMock()

    # Track which nodes get executed
    executed_nodes: list[str] = []

    mock_llm.generate = AsyncMock(return_value="# Strategy Document\nGenerated Strategy")

    # Mock node functions
    with patch("homecare_agent.graph.main_graph.intake_feature") as mock_intake, \
         patch("homecare_agent.graph.main_graph.analyze_codebase") as mock_analyze, \
         patch("homecare_agent.graph.main_graph.generate_strategy") as mock_strategy:

        async def fake_intake(state, **kwargs):
            executed_nodes.append("intake_feature")
            return {"current_step": "intake_feature"}

        async def fake_analyze(state, **kwargs):
            executed_nodes.append("analyze_codebase")
            return {"current_step": "analyze_codebase"}

        async def fake_strategy(state, **kwargs):
            executed_nodes.append("generate_strategy")
            # Return strategy to test pipeline continuation
            return {
                "current_step": "generate_strategy",
                "strategy_document": "# Strategy for Caregiver Feature",
            }

        mock_intake.side_effect = fake_intake
        mock_analyze.side_effect = fake_analyze
        mock_strategy.side_effect = fake_strategy

        # Compile graph
        compiled_graph = compile_graph(settings, mock_llm)

        # State restored from checkpoint after Step 3 (analyze_codebase)
        resume_state: AgentState = {
            "trace_id": "test_resume_trace",
            "feature_name": "Test Resumed Feature",
            "feature_description": "Resumed from Step 4",
            "codebase_analysis": {"analysis": "complete"},
            "completed_steps": ["intake_feature", "analyze_codebase"],
            "resume_from_step": "generate_strategy",  # Instruct graph to start at Step 4!
        }

        # Run first step of stream
        async for event in compiled_graph.astream(resume_state):
            for node_name in event:
                if node_name == "generate_strategy":
                    # We reached step 4!
                    break
            break

        # VERIFICATION:
        # 1. Step 1 (intake_feature) was NEVER called
        assert "intake_feature" not in executed_nodes
        mock_intake.assert_not_called()

        # 2. Step 3 (analyze_codebase) was NEVER called
        assert "analyze_codebase" not in executed_nodes
        mock_analyze.assert_not_called()

        # 3. Step 4 (generate_strategy) WAS called directly from START!
        assert "generate_strategy" in executed_nodes
        mock_strategy.assert_called_once()


# ─── CLI Resume Tests ────────────────────────────────────────────────────────


def test_cli_resume_list_empty(tmp_path: Path):
    """Verify CLI resume --list shows empty message when no checkpoints exist."""
    with patch("homecare_agent.graph.checkpoint.CheckpointManager") as MockMgr:
        instance = MockMgr.return_value
        instance.list_checkpoints.return_value = []
        result = runner.invoke(app, ["resume", "--list"])
        assert result.exit_code == 0
        assert "No checkpoints found" in result.output


def test_cli_resume_list_with_data(tmp_path: Path):
    """Verify CLI resume --list displays tabular summary of saved checkpoints."""
    with patch("homecare_agent.graph.checkpoint.CheckpointManager") as MockMgr:
        instance = MockMgr.return_value
        instance.list_checkpoints.return_value = [
            {
                "trace_id": "abcdef1234567890abcdef1234567890",
                "feature_name": "Patient Intake Flow",
                "last_completed_step": "analyze_codebase",
                "last_completed_step_number": 3,
                "next_recommended_step": "generate_strategy",
                "timestamp": "2026-09-17T02:00:00Z",
            }
        ]
        result = runner.invoke(app, ["resume", "--list"])
        assert result.exit_code == 0
        assert "Patient" in result.output
        assert "Step 3" in result.output
        assert "Step 4" in result.output
