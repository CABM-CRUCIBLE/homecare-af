# Author: C A B M
# Date: 2026-09-17

"""Conditional routing logic for the LangGraph workflow.

Defines edge functions that determine the next node to execute
based on the current state. These implement the decision diamonds
in the workflow graph.
"""

from __future__ import annotations

import logging
from typing import Literal

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState

logger = logging.getLogger(__name__)


def needs_clarification(
    state: AgentState,
    settings: Settings | None = None,
) -> Literal["ask_clarifications", "analyze_codebase"]:
    """Route based on whether clarification is needed.

    Returns:
        Next node name: either ask_clarifications or analyze_codebase.
    """
    trace_id = state.get("trace_id", "no-trace")
    max_clarifications = settings.max_clarification_iterations if settings else 2
    clarification_iteration = state.get("clarification_iteration", 0)

    if not state.get("clarification_complete", False):
        if clarification_iteration >= max_clarifications:
            logger.warning(
                "[ROUTE:needs_clarification][trace_id=%s] Decision -> 'analyze_codebase' (clarification limit %d/%d reached, progressing)",
                trace_id,
                clarification_iteration,
                max_clarifications,
            )
            return "analyze_codebase"
        logger.info(
            "[ROUTE:needs_clarification][trace_id=%s] Decision -> 'ask_clarifications' (clarifications pending, iter %d/%d)",
            trace_id,
            clarification_iteration,
            max_clarifications,
        )
        return "ask_clarifications"
    logger.info(
        "[ROUTE:needs_clarification][trace_id=%s] Decision -> 'analyze_codebase' (clarifications complete)",
        trace_id,
    )
    return "analyze_codebase"


def arch_approved(
    state: AgentState,
    settings: Settings | None = None,
) -> Literal["create_branch", "revise_architecture"]:
    """Route based on architecture review approval.

    Returns:
        Next node name: create_branch if approved, revise_architecture if not.
    """
    trace_id = state.get("trace_id", "no-trace")
    max_arch = settings.max_arch_iterations if settings else 3
    arch_iteration = state.get("arch_iteration", 0)

    if state.get("architecture_approved", False):
        logger.info(
            "[ROUTE:arch_approved][trace_id=%s] Decision -> 'create_branch' (architecture approved)",
            trace_id,
        )
        return "create_branch"

    if arch_iteration >= max_arch:
        logger.warning(
            "[ROUTE:arch_approved][trace_id=%s] Decision -> 'create_branch' (architecture review loop limit %d/%d reached, forcing proceed to avoid runaway spend)",
            trace_id,
            arch_iteration,
            max_arch,
        )
        return "create_branch"

    logger.info(
        "[ROUTE:arch_approved][trace_id=%s] Decision -> 'revise_architecture' (architecture requires revision, iter %d/%d)",
        trace_id,
        arch_iteration,
        max_arch,
    )
    return "revise_architecture"


def more_waves(state: AgentState, settings: Settings | None = None) -> Literal["execute_wave", "run_e2e_tests"]:
    """Route based on whether more waves remain.

    Returns:
        Next node name: execute_wave if more waves, run_e2e_tests if done.
    """
    trace_id = state.get("trace_id", "no-trace")
    current_wave = state.get("current_wave", 0)
    work_packages = state.get("work_packages", [])

    # Count distinct waves
    waves = {wp.get("wave", "") for wp in work_packages}
    if current_wave < len(waves):
        logger.info(
            "[ROUTE:more_waves][trace_id=%s] Decision -> 'execute_wave' (wave %d of %d)",
            trace_id,
            current_wave + 1,
            len(waves),
        )
        return "execute_wave"
    logger.info(
        "[ROUTE:more_waves][trace_id=%s] Decision -> 'run_e2e_tests' (all %d wave(s) completed)",
        trace_id,
        len(waves),
    )
    return "run_e2e_tests"


def changes_needed(state: AgentState, settings: Settings | None = None) -> Literal["apply_review_fixes", "post_review_comments"]:
    """Route based on whether code review found changes needed.

    Returns:
        Next node name: apply_review_fixes or post_review_comments.
    """
    trace_id = state.get("trace_id", "no-trace")
    max_iterations = 3
    if settings:
        max_iterations = settings.max_review_iterations

    review_iteration = state.get("review_iteration", 0)
    needed = state.get("review_changes_needed", False)

    if needed and review_iteration < max_iterations:
        logger.info(
            "[ROUTE:changes_needed][trace_id=%s] Decision -> 'apply_review_fixes' (iteration %d/%d, changes requested)",
            trace_id,
            review_iteration,
            max_iterations,
        )
        return "apply_review_fixes"
    logger.info(
        "[ROUTE:changes_needed][trace_id=%s] Decision -> 'post_review_comments' (iteration %d/%d, changes_needed=%s)",
        trace_id,
        review_iteration,
        max_iterations,
        needed,
    )
    return "post_review_comments"

