# Author: C A B M
# Date: 2026-09-17

"""Main LangGraph workflow assembly.

Compiles the full StateGraph with all nodes and conditional edges,
implementing the complete agentic code generation pipeline:

  START → intake → [clarification loop] → analyze → strategy → tactical →
  ADRs → prompts → [arch review loop] → branch → [wave execution loop] →
  E2E tests → load tests → commit tests → manual test doc → commit docs →
  PR → [code review loop] → notify → END
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from homecare_agent.config import Settings
from homecare_agent.graph.edges.routing import (
    arch_approved,
    changes_needed,
    check_prompts_output,
    check_strategy_output,
    check_tactical_output,
    more_waves,
    needs_clarification,
)
from homecare_agent.graph.nodes.analyze import analyze_codebase
from homecare_agent.graph.nodes.architect import (
    generate_adrs,
    generate_strategy,
    generate_tactical_plan,
)
from homecare_agent.graph.nodes.clarification import ask_clarifications
from homecare_agent.graph.nodes.code_review import (
    apply_review_fixes,
    perform_code_review,
)
from homecare_agent.graph.nodes.documentation import generate_manual_test_doc
from homecare_agent.graph.nodes.execute_prompt import execute_wave, write_generated_files
from homecare_agent.graph.nodes.generate_prompts import generate_agentic_prompts
from homecare_agent.graph.nodes.git_ops import (
    commit_and_push,
    create_branch,
    create_pull_request,
)
from homecare_agent.graph.nodes.intake import intake_feature
from homecare_agent.graph.nodes.notifications import (
    error_halt,
    notify_completion,
    post_review_comments,
)
from homecare_agent.graph.nodes.review_arch import review_architecture, revise_architecture
from homecare_agent.graph.nodes.testing import run_tests
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


def build_graph(settings: Settings, llm: LLMProvider) -> StateGraph:
    """Build and compile the main LangGraph workflow.

    Args:
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = StateGraph(AgentState)

    # ─── Node Registration ───────────────────────────────────────────────
    # Each node is a partial function bound to settings and llm

    graph.add_node("intake_feature", partial(intake_feature, settings=settings, llm=llm))
    graph.add_node("ask_clarifications", partial(ask_clarifications, settings=settings, llm=llm))
    graph.add_node("analyze_codebase", partial(analyze_codebase, settings=settings, llm=llm))
    graph.add_node("generate_strategy", partial(generate_strategy, settings=settings, llm=llm))
    graph.add_node("generate_tactical_plan", partial(generate_tactical_plan, settings=settings, llm=llm))
    graph.add_node("generate_adrs", partial(generate_adrs, settings=settings, llm=llm))
    graph.add_node("generate_agentic_prompts", partial(generate_agentic_prompts, settings=settings, llm=llm))
    graph.add_node("review_architecture", partial(review_architecture, settings=settings, llm=llm))
    graph.add_node("revise_architecture", partial(revise_architecture, settings=settings, llm=llm))
    graph.add_node("create_branch", partial(create_branch, settings=settings))
    graph.add_node("execute_wave", partial(execute_wave, settings=settings, llm=llm))
    graph.add_node("write_files", partial(write_generated_files, settings=settings))
    graph.add_node("run_unit_tests", partial(run_tests, settings=settings, test_type="unit"))
    graph.add_node("commit_wave", partial(commit_and_push, settings=settings, step_name="commit_wave"))
    graph.add_node("run_e2e_tests", partial(run_tests, settings=settings, test_type="e2e"))
    graph.add_node("run_load_tests", partial(run_tests, settings=settings, test_type="load"))
    graph.add_node("commit_test_suite", partial(commit_and_push, settings=settings, step_name="commit_tests"))
    graph.add_node("generate_manual_test_doc", partial(generate_manual_test_doc, settings=settings, llm=llm))
    graph.add_node("commit_documentation", partial(commit_and_push, settings=settings, step_name="commit_docs"))
    graph.add_node("create_pr", partial(create_pull_request, settings=settings, llm=llm))
    graph.add_node("perform_code_review", partial(perform_code_review, settings=settings, llm=llm))
    graph.add_node("apply_review_fixes", partial(apply_review_fixes, settings=settings, llm=llm))
    graph.add_node("commit_fixes", partial(commit_and_push, settings=settings, step_name="commit_fixes"))
    graph.add_node("post_review_comments", partial(post_review_comments, settings=settings))
    graph.add_node("notify_ready_for_merge", partial(notify_completion, settings=settings))
    graph.add_node("error_halt", partial(error_halt, settings=settings))

    # ─── Edge Wiring ─────────────────────────────────────────────────────

    # ─── Dynamic Entry Routing ───────────────────────────────────────────
    # Supports starting fresh at intake_feature OR resuming from any step (e.g. Step 4)
    from homecare_agent.graph.checkpoint import ENTRY_ELIGIBLE_NODES

    def _route_entry(state: AgentState) -> str:
        resume_step = state.get("resume_from_step")
        if resume_step and resume_step in ENTRY_ELIGIBLE_NODES:
            logger.info("[RESUME:ENTRY] Resuming workflow directly from step '%s'", resume_step)
            return resume_step
        return "intake_feature"

    entry_targets = {node: node for node in ENTRY_ELIGIBLE_NODES}
    entry_targets["intake_feature"] = "intake_feature"
    graph.add_conditional_edges(START, _route_entry, entry_targets)

    # Clarification loop
    graph.add_conditional_edges("intake_feature", partial(needs_clarification, settings=settings))
    graph.add_edge("ask_clarifications", "intake_feature")

    # Architecture pipeline with sentinel error-halting edges (ARCH-01)
    graph.add_edge("analyze_codebase", "generate_strategy")
    graph.add_conditional_edges("generate_strategy", partial(check_strategy_output, settings=settings))
    graph.add_conditional_edges("generate_tactical_plan", partial(check_tactical_output, settings=settings))
    graph.add_edge("generate_adrs", "generate_agentic_prompts")
    graph.add_conditional_edges("generate_agentic_prompts", partial(check_prompts_output, settings=settings))

    # Architecture review loop
    graph.add_conditional_edges("review_architecture", partial(arch_approved, settings=settings))
    graph.add_edge("revise_architecture", "review_architecture")

    # Execution pipeline
    graph.add_edge("create_branch", "execute_wave")
    graph.add_edge("execute_wave", "write_files")
    graph.add_edge("write_files", "run_unit_tests")
    graph.add_edge("run_unit_tests", "commit_wave")

    # Wave loop
    graph.add_conditional_edges("commit_wave", partial(more_waves, settings=settings))

    # Testing pipeline
    graph.add_edge("run_e2e_tests", "run_load_tests")
    graph.add_edge("run_load_tests", "commit_test_suite")
    graph.add_edge("commit_test_suite", "generate_manual_test_doc")
    graph.add_edge("generate_manual_test_doc", "commit_documentation")

    # PR and review
    graph.add_edge("commit_documentation", "create_pr")
    graph.add_edge("create_pr", "perform_code_review")

    # Code review loop
    graph.add_conditional_edges("perform_code_review", partial(changes_needed, settings=settings))
    graph.add_edge("apply_review_fixes", "commit_fixes")
    graph.add_edge("commit_fixes", "perform_code_review")

    # Completion & Error Halting
    graph.add_edge("post_review_comments", "notify_ready_for_merge")
    graph.add_edge("notify_ready_for_merge", END)
    graph.add_edge("error_halt", END)

    return graph


def compile_graph(settings: Settings, llm: LLMProvider) -> Any:
    """Build and compile the graph into a runnable.

    Args:
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        A compiled LangGraph runnable.
    """
    graph = build_graph(settings, llm)
    compiled = graph.compile()
    logger.info("LangGraph workflow compiled with %d nodes.", len(graph.nodes))
    return compiled


# ─── Backward Compatibility Aliases (ARCH-03) ───────────────────────────
# Node implementations have been modularized into dedicated packages:
# - ask_clarifications -> homecare_agent.graph.nodes.clarification
# - revise_architecture -> homecare_agent.graph.nodes.review_arch
# - run_tests -> homecare_agent.graph.nodes.testing
# - generate_manual_test_doc -> homecare_agent.graph.nodes.documentation
# - post_review_comments -> homecare_agent.graph.nodes.notifications
# - notify_completion -> homecare_agent.graph.nodes.notifications

_ask_clarifications = ask_clarifications
_revise_architecture = revise_architecture
_run_tests = run_tests
_generate_manual_test_doc = generate_manual_test_doc
_post_review_comments = post_review_comments
_notify_completion = notify_completion
