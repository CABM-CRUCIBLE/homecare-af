# Author: C A B M
# Date: 2026-09-17

"""Unit tests for LangGraph state and routing logic."""

from unittest.mock import MagicMock

from homecare_agent.config import Settings
from homecare_agent.graph.edges.routing import (
    arch_approved,
    changes_needed,
    more_waves,
    needs_clarification,
)
from homecare_agent.graph.main_graph import build_graph
from homecare_agent.graph.state import AgentState, append_list, merge_dicts


def test_merge_dicts():
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 3, "c": 4}
    merged = merge_dicts(d1, d2)
    assert merged == {"a": 1, "b": 3, "c": 4}


def test_append_list():
    l1 = [{"id": "1", "val": "a"}]
    l2 = [{"id": "1", "val": "a_duplicate"}, {"id": "2", "val": "b"}]
    result = append_list(l1, l2)
    assert len(result) == 2
    assert result[0]["val"] == "a"
    assert result[1]["id"] == "2"


def test_routing_needs_clarification():
    state1: AgentState = {"clarification_complete": False}
    assert needs_clarification(state1) == "ask_clarifications"

    state2: AgentState = {"clarification_complete": True}
    assert needs_clarification(state2) == "analyze_codebase"


def test_routing_arch_approved():
    state_approved: AgentState = {"architecture_approved": True}
    assert arch_approved(state_approved) == "create_branch"

    state_rejected: AgentState = {"architecture_approved": False}
    assert arch_approved(state_rejected) == "revise_architecture"


def test_routing_more_waves():
    state_more: AgentState = {
        "current_wave": 1,
        "work_packages": [{"wave": "Wave 1"}, {"wave": "Wave 2"}],
    }
    assert more_waves(state_more) == "execute_wave"

    state_done: AgentState = {
        "current_wave": 2,
        "work_packages": [{"wave": "Wave 1"}, {"wave": "Wave 2"}],
    }
    assert more_waves(state_done) == "run_e2e_tests"


def test_routing_changes_needed():
    settings = Settings(openrouter_api_key="test-key", max_review_iterations=3)

    state_fixes: AgentState = {
        "review_changes_needed": True,
        "review_iteration": 1,
    }
    assert changes_needed(state_fixes, settings) == "apply_review_fixes"

    state_max_iter: AgentState = {
        "review_changes_needed": True,
        "review_iteration": 3,
    }
    assert changes_needed(state_max_iter, settings) == "post_review_comments"

    state_approved: AgentState = {
        "review_changes_needed": False,
        "review_iteration": 1,
    }
    assert changes_needed(state_approved, settings) == "post_review_comments"


def test_build_graph():
    settings = Settings(openrouter_api_key="test-key")
    mock_llm = MagicMock()
    compiled_graph = build_graph(settings, mock_llm)
    assert compiled_graph is not None
