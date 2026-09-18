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
            is_cost_saver = (
                state.get("stop_after_clarification")
                or (settings.cost_saver_mode if settings else False)
                or state.get("stop_after_step") in ("intake_feature", "ask_clarifications", "1", "2")
            )
            if is_cost_saver:
                logger.info("[ROUTE:needs_clarification][trace_id=%s] Decision -> END (cost-saver stop_after_clarification active)", trace_id)
                return "__end__"  # type: ignore[return-value]
            return "analyze_codebase"
        logger.info(
            "[ROUTE:needs_clarification][trace_id=%s] Decision -> 'ask_clarifications' (clarifications pending, iter %d/%d)",
            trace_id,
            clarification_iteration,
            max_clarifications,
        )
        return "ask_clarifications"

    # Clarifications complete
    is_cost_saver = (
        state.get("stop_after_clarification")
        or (settings.cost_saver_mode if settings else False)
        or state.get("stop_after_step") in ("intake_feature", "ask_clarifications", "1", "2")
    )
    if is_cost_saver:
        logger.info("[ROUTE:needs_clarification][trace_id=%s] Decision -> END (cost-saver stop_after_clarification active)", trace_id)
        return "__end__"  # type: ignore[return-value]

    logger.info(
        "[ROUTE:needs_clarification][trace_id=%s] Decision -> 'analyze_codebase' (clarifications complete)",
        trace_id,
    )
    return "analyze_codebase"


def arch_approved(
    state: AgentState,
    settings: Settings | None = None,
) -> Literal["create_branch", "revise_architecture"]:
    """Route based on architecture review approval (ARCH-03 single-pass review).

    Returns:
        Next node name: create_branch if approved or review already completed once,
        revise_architecture if findings need to be applied.
    """
    trace_id = state.get("trace_id", "no-trace")
    max_arch = settings.max_arch_iterations if settings else 1
    arch_iteration = state.get("arch_iteration", 0)

    if state.get("architecture_approved", False):
        logger.info(
            "[ROUTE:arch_approved][trace_id=%s] Decision -> 'create_branch' (architecture approved)",
            trace_id,
        )
        return "create_branch"

    if arch_iteration >= max_arch:
        logger.info(
            "[ROUTE:arch_approved][trace_id=%s] Decision -> 'create_branch' (architecture review single-pass complete, iter %d/%d)",
            trace_id,
            arch_iteration,
            max_arch,
        )
        return "create_branch"

    logger.info(
        "[ROUTE:arch_approved][trace_id=%s] Decision -> 'revise_architecture' (applying architecture review findings to documentation)",
        trace_id,
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

    # Count distinct waves (matching execute_wave ordering and grouping, filtering empty wave IDs - EDGE-01)
    wave_ids = sorted(list({str(wp["wave"]) for wp in work_packages if wp.get("wave")}))
    total_waves = len(wave_ids)
    if current_wave < total_waves:
        logger.info(
            "[ROUTE:more_waves][trace_id=%s] Decision -> 'execute_wave' (wave %d of %d)",
            trace_id,
            current_wave + 1,
            total_waves,
        )
        return "execute_wave"
    logger.info(
        "[ROUTE:more_waves][trace_id=%s] Decision -> 'run_e2e_tests' (all %d wave(s) completed)",
        trace_id,
        total_waves,
    )
    return "run_e2e_tests"


# ─── Sentinel Error-Halting Edges (ARCH-01) ──────────────────────────────────


def check_strategy_output(state: AgentState, settings: Settings | None = None) -> Literal["generate_tactical_plan", "error_halt"]:
    """Sentinel edge checking whether generate_strategy produced a valid strategy document (ARCH-01)."""
    trace_id = state.get("trace_id", "no-trace")
    strategy_doc = state.get("strategy_document", "")
    if not strategy_doc or not strategy_doc.strip() or "Generation failed" in strategy_doc:
        logger.critical(
            "[ROUTE:check_strategy_output][trace_id=%s] Decision -> 'error_halt' (strategy_document missing or generation failed)",
            trace_id,
        )
        return "error_halt"
    logger.info(
        "[ROUTE:check_strategy_output][trace_id=%s] Decision -> 'generate_tactical_plan' (strategy document verified, %d chars)",
        trace_id,
        len(strategy_doc),
    )
    return "generate_tactical_plan"


def check_tactical_output(state: AgentState, settings: Settings | None = None) -> Literal["generate_adrs", "error_halt"]:
    """Sentinel edge checking whether generate_tactical_plan produced valid plan and work packages (ARCH-01)."""
    trace_id = state.get("trace_id", "no-trace")
    tactical_plan = state.get("tactical_plan", "")
    if not tactical_plan or not tactical_plan.strip() or "Generation failed" in tactical_plan:
        logger.critical(
            "[ROUTE:check_tactical_output][trace_id=%s] Decision -> 'error_halt' (tactical_plan missing or generation failed)",
            trace_id,
        )
        return "error_halt"
    work_packages = state.get("work_packages", [])
    logger.info(
        "[ROUTE:check_tactical_output][trace_id=%s] Decision -> 'generate_adrs' (tactical plan verified, %d WPs)",
        trace_id,
        len(work_packages),
    )
    return "generate_adrs"


def check_prompts_output(state: AgentState, settings: Settings | None = None) -> Literal["review_architecture", "error_halt"]:
    """Sentinel edge checking whether generate_agentic_prompts produced valid prompts and instructions (ARCH-01)."""
    trace_id = state.get("trace_id", "no-trace")
    standing_instructions = state.get("standing_instructions", "")
    errors = state.get("errors", [])
    prompt_errors = [e for e in errors if isinstance(e, dict) and e.get("step") == "generate_agentic_prompts"]
    if prompt_errors and not standing_instructions:
        logger.critical(
            "[ROUTE:check_prompts_output][trace_id=%s] Decision -> 'error_halt' (prompt generation encountered unrecoverable errors)",
            trace_id,
        )
        return "error_halt"
    logger.info(
        "[ROUTE:check_prompts_output][trace_id=%s] Decision -> 'review_architecture' (prompts verified)",
        trace_id,
    )
    return "review_architecture"


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

