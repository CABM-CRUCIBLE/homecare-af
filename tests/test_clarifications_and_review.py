# Author: C A B M
# Date: 2026-09-17

"""Tests for wireframe file extraction, interactive clarifications, and single-pass architecture review."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.edges.routing import arch_approved
from homecare_agent.graph.main_graph import compile_graph
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider
from homecare_agent.ui.clarification_manager import ClarificationManager
from homecare_agent.ui.web import _extract_file_paths


def test_extract_file_paths(tmp_path) -> None:
    """Verify file path extraction from paths, FileData objects, and dicts."""
    test_file = tmp_path / "wireframe.png"
    test_file.write_bytes(b"fake-image-bytes")

    # String path
    assert _extract_file_paths([str(test_file)]) == [str(test_file)]

    # Object with .path
    mock_file_data = MagicMock()
    mock_file_data.path = str(test_file)
    del mock_file_data.name
    assert _extract_file_paths([mock_file_data]) == [str(test_file)]

    # Dict with 'path'
    assert _extract_file_paths([{"path": str(test_file)}]) == [str(test_file)]

    # Non-existent file ignored
    assert _extract_file_paths(["/non/existent/path.png"]) == []

    # None / empty
    assert _extract_file_paths(None) == []
    assert _extract_file_paths([]) == []


@pytest.mark.asyncio
async def test_clarification_manager_flow() -> None:
    """Verify ClarificationManager registers, waits for, and receives answers asynchronously."""
    mgr = ClarificationManager()
    trace_id = "test-trace-12345"

    session = mgr.register_session(trace_id)
    assert mgr.has_session(trace_id)

    questions = [{"id": "Q1", "question": "What database to use?", "category": "Storage"}]
    fut = mgr.request_clarification(trace_id, questions)
    assert not fut.done()

    async def user_answers_later():
        await asyncio.sleep(0.05)
        mgr.submit_answer("PostgreSQL", trace_id=trace_id)

    task = asyncio.create_task(user_answers_later())
    ans = await mgr.wait_for_answer(trace_id, timeout=2.0)
    await task

    assert ans == "PostgreSQL"
    assert fut.done()
    assert fut.result() == "PostgreSQL"

    mgr.clear_session(trace_id)
    assert not mgr.has_session(trace_id)


def test_arch_review_single_pass_routing() -> None:
    """Verify arch_approved routes to revise on first pass and create_branch once complete."""
    settings = Settings(max_arch_iterations=1)

    # Approved directly
    state_approved: AgentState = {"architecture_approved": True, "arch_iteration": 0}
    assert arch_approved(state_approved, settings) == "create_branch"

    # Needs revision on iteration 0
    state_revise: AgentState = {"architecture_approved": False, "arch_iteration": 0}
    assert arch_approved(state_revise, settings) == "revise_architecture"

    # Single-pass limit reached (arch_iteration >= 1)
    state_limit: AgentState = {"architecture_approved": False, "arch_iteration": 1}
    assert arch_approved(state_limit, settings) == "create_branch"


def test_cost_saver_mode_halts_after_clarifications() -> None:
    """Verify needs_clarification routes to __end__ when cost-saver stop_after_clarification is active."""
    from homecare_agent.graph.edges.routing import needs_clarification
    settings = Settings(max_clarification_iterations=2)

    # If clarifications are still pending, continue asking
    state_pending: AgentState = {
        "clarification_complete": False,
        "clarification_iteration": 0,
        "stop_after_clarification": True,
    }
    assert needs_clarification(state_pending, settings) == "ask_clarifications"

    # Once clarifications are complete, cost-saver halts execution at __end__
    state_complete: AgentState = {
        "clarification_complete": True,
        "clarification_iteration": 1,
        "stop_after_clarification": True,
    }
    assert needs_clarification(state_complete, settings) == "__end__"

    # Without cost-saver mode, progresses to analyze_codebase
    state_normal: AgentState = {
        "clarification_complete": True,
        "clarification_iteration": 1,
        "stop_after_clarification": False,
    }
    assert needs_clarification(state_normal, settings) == "analyze_codebase"


def test_graph_revise_architecture_targets_create_branch() -> None:
    """Verify in the compiled graph that revise_architecture moves directly to create_branch."""
    settings = Settings(openrouter_api_key="sk-test", langfuse_enabled=False)
    llm = LLMProvider(settings)
    graph = compile_graph(settings, llm)

    # In langgraph, graph structure edges can be inspected
    # In langgraph, builder edges can be directly verified
    assert ("revise_architecture", "create_branch") in graph.builder.edges
    assert ("revise_architecture", "review_architecture") not in graph.builder.edges
