# Author: C A B M
# Date: 2026-09-17

"""Conditional routing logic for the LangGraph workflow.

Defines edge functions that determine the next node to execute
based on the current state. These implement the decision diamonds
in the workflow graph.
"""

from __future__ import annotations

from typing import Literal

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState


def needs_clarification(state: AgentState) -> Literal["ask_clarifications", "analyze_codebase"]:
    """Route based on whether clarification is needed.

    Returns:
        Next node name: either ask_clarifications or analyze_codebase.
    """
    if not state.get("clarification_complete", False):
        return "ask_clarifications"
    return "analyze_codebase"


def arch_approved(state: AgentState) -> Literal["create_branch", "revise_architecture"]:
    """Route based on architecture review approval.

    Returns:
        Next node name: create_branch if approved, revise_architecture if not.
    """
    if state.get("architecture_approved", False):
        return "create_branch"
    return "revise_architecture"


def more_waves(state: AgentState, settings: Settings | None = None) -> Literal["execute_wave", "run_e2e_tests"]:
    """Route based on whether more waves remain.

    Returns:
        Next node name: execute_wave if more waves, run_e2e_tests if done.
    """
    current_wave = state.get("current_wave", 0)
    work_packages = state.get("work_packages", [])

    # Count distinct waves
    waves = {wp.get("wave", "") for wp in work_packages}
    if current_wave < len(waves):
        return "execute_wave"
    return "run_e2e_tests"


def changes_needed(state: AgentState, settings: Settings | None = None) -> Literal["apply_review_fixes", "post_review_comments"]:
    """Route based on whether code review found changes needed.

    Returns:
        Next node name: apply_review_fixes or post_review_comments.
    """
    max_iterations = 3
    if settings:
        max_iterations = settings.max_review_iterations

    review_iteration = state.get("review_iteration", 0)

    if state.get("review_changes_needed", False) and review_iteration < max_iterations:
        return "apply_review_fixes"
    return "post_review_comments"
