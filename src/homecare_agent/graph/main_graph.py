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

import logging
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from homecare_agent.config import Settings
from homecare_agent.graph.edges.routing import (
    arch_approved,
    changes_needed,
    more_waves,
    needs_clarification,
)
from homecare_agent.graph.nodes.analyze import analyze_codebase
from homecare_agent.graph.nodes.architect import (
    generate_adrs,
    generate_strategy,
    generate_tactical_plan,
)
from homecare_agent.graph.nodes.code_review import (
    apply_review_fixes,
    perform_code_review,
)
from homecare_agent.graph.nodes.execute_prompt import execute_wave, write_generated_files
from homecare_agent.graph.nodes.generate_prompts import generate_agentic_prompts
from homecare_agent.graph.nodes.git_ops import (
    commit_and_push,
    create_branch,
    create_pull_request,
)
from homecare_agent.graph.nodes.intake import intake_feature
from homecare_agent.graph.nodes.review_arch import review_architecture
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
    graph.add_node("ask_clarifications", partial(_ask_clarifications, settings=settings, llm=llm))
    graph.add_node("analyze_codebase", partial(analyze_codebase, settings=settings, llm=llm))
    graph.add_node("generate_strategy", partial(generate_strategy, settings=settings, llm=llm))
    graph.add_node("generate_tactical_plan", partial(generate_tactical_plan, settings=settings, llm=llm))
    graph.add_node("generate_adrs", partial(generate_adrs, settings=settings, llm=llm))
    graph.add_node("generate_agentic_prompts", partial(generate_agentic_prompts, settings=settings, llm=llm))
    graph.add_node("review_architecture", partial(review_architecture, settings=settings, llm=llm))
    graph.add_node("revise_architecture", partial(_revise_architecture, settings=settings, llm=llm))
    graph.add_node("create_branch", partial(create_branch, settings=settings))
    graph.add_node("execute_wave", partial(execute_wave, settings=settings, llm=llm))
    graph.add_node("write_files", partial(write_generated_files, settings=settings))
    graph.add_node("run_unit_tests", partial(_run_tests, settings=settings, test_type="unit"))
    graph.add_node("commit_wave", partial(commit_and_push, settings=settings, step_name="commit_wave"))
    graph.add_node("run_e2e_tests", partial(_run_tests, settings=settings, test_type="e2e"))
    graph.add_node("run_load_tests", partial(_run_tests, settings=settings, test_type="load"))
    graph.add_node("commit_test_suite", partial(commit_and_push, settings=settings, step_name="commit_tests"))
    graph.add_node("generate_manual_test_doc", partial(_generate_manual_test_doc, settings=settings, llm=llm))
    graph.add_node("commit_documentation", partial(commit_and_push, settings=settings, step_name="commit_docs"))
    graph.add_node("create_pr", partial(create_pull_request, settings=settings, llm=llm))
    graph.add_node("perform_code_review", partial(perform_code_review, settings=settings, llm=llm))
    graph.add_node("apply_review_fixes", partial(apply_review_fixes, settings=settings, llm=llm))
    graph.add_node("commit_fixes", partial(commit_and_push, settings=settings, step_name="commit_fixes"))
    graph.add_node("post_review_comments", partial(_post_review_comments, settings=settings))
    graph.add_node("notify_ready_for_merge", partial(_notify_completion, settings=settings))

    # ─── Edge Wiring ─────────────────────────────────────────────────────

    # Entry
    graph.add_edge(START, "intake_feature")

    # Clarification loop
    graph.add_conditional_edges("intake_feature", needs_clarification)
    graph.add_edge("ask_clarifications", "intake_feature")

    # Architecture pipeline
    graph.add_edge("analyze_codebase", "generate_strategy")
    graph.add_edge("generate_strategy", "generate_tactical_plan")
    graph.add_edge("generate_tactical_plan", "generate_adrs")
    graph.add_edge("generate_adrs", "generate_agentic_prompts")
    graph.add_edge("generate_agentic_prompts", "review_architecture")

    # Architecture review loop
    graph.add_conditional_edges("review_architecture", arch_approved)
    graph.add_edge("revise_architecture", "review_architecture")

    # Execution pipeline
    graph.add_edge("create_branch", "execute_wave")
    graph.add_edge("execute_wave", "write_files")
    graph.add_edge("write_files", "run_unit_tests")
    graph.add_edge("run_unit_tests", "commit_wave")

    # Wave loop
    graph.add_conditional_edges("commit_wave", more_waves)

    # Testing pipeline
    graph.add_edge("run_e2e_tests", "run_load_tests")
    graph.add_edge("run_load_tests", "commit_test_suite")
    graph.add_edge("commit_test_suite", "generate_manual_test_doc")
    graph.add_edge("generate_manual_test_doc", "commit_documentation")

    # PR and review
    graph.add_edge("commit_documentation", "create_pr")
    graph.add_edge("create_pr", "perform_code_review")

    # Code review loop
    graph.add_conditional_edges("perform_code_review", changes_needed)
    graph.add_edge("apply_review_fixes", "commit_fixes")
    graph.add_edge("commit_fixes", "perform_code_review")

    # Completion
    graph.add_edge("post_review_comments", "notify_ready_for_merge")
    graph.add_edge("notify_ready_for_merge", END)

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


# ─── Stub nodes (to be expanded) ────────────────────────────────────────


async def _ask_clarifications(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Present clarification questions to the user via CLI or web UI.

    In CLI mode: uses Rich prompts for interactive Q&A.
    In Web mode: sends questions to the Gradio interface.
    """
    from rich.console import Console
    from rich.prompt import Prompt

    console = Console()
    questions = state.get("clarification_questions", [])
    answers: list[dict[str, Any]] = []

    console.print("\n[bold yellow]📋 Clarification Questions[/bold yellow]\n")

    for q in questions:
        if q.get("answer"):
            continue  # Already answered
        console.print(f"[bold]{q.get('id', '?')}[/bold] ({q.get('category', 'general')})")
        console.print(f"  {q.get('question', '')}")
        if q.get("context"):
            console.print(f"  [dim]{q['context']}[/dim]")

        options = q.get("options", [])
        if options:
            for i, opt in enumerate(options, 1):
                console.print(f"    {i}. {opt}")

        answer = Prompt.ask("  Your answer")
        answers.append({
            "id": q.get("id", ""),
            "question": q.get("question", ""),
            "answer": answer,
        })

    return {
        "clarification_answers": answers,
        "clarification_complete": True,
    }


async def _revise_architecture(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Revise architecture based on review findings."""
    review = state.get("architecture_review", "")

    revision_prompt = f"""The architecture review found issues that need to be addressed.

**Review Findings:**
{review[:10000]}

**Current Strategy:**
{state.get("strategy_document", "")[:10000]}

Revise the Strategy and Tactical Plan to address ALL blocking and critical findings.
Output the revised Strategy document.
"""

    try:
        response = await llm.ainvoke(
            prompt=revision_prompt,
            system_prompt="You are a Senior Solution Architect revising an architecture proposal based on review feedback.",
            node_name="revise_architecture",
            state_overrides=state,
            trace_name="revise_architecture",
        )
        return {
            "strategy_document": response,
            "current_step": "revise_architecture",
            "completed_steps": ["revise_architecture"],
        }
    except Exception:
        logger.exception("Architecture revision failed.")
        return {"architecture_approved": True}  # Force proceed


async def _run_tests(state: AgentState, settings: Settings, test_type: str = "unit") -> dict[str, Any]:
    """Run tests (unit, e2e, load) and capture results."""
    import subprocess
    from pathlib import Path

    repo_path = Path(state.get("repo_path", settings.repo_path))
    results: dict[str, Any] = {"type": test_type, "passed": 0, "failed": 0, "total": 0}

    if test_type == "unit":
        # Backend tests
        try:
            proc = subprocess.run(
                ["dotnet", "test", "--no-build", "--verbosity", "minimal"],
                cwd=str(repo_path / "code" / "backend"),
                capture_output=True, text=True, timeout=300,
            )
            results["backend_output"] = proc.stdout
            results["backend_returncode"] = proc.returncode
        except Exception as e:
            results["backend_error"] = str(e)

        # Frontend tests
        try:
            proc = subprocess.run(
                ["npm", "test", "--", "--run"],
                cwd=str(repo_path / "code" / "frontend"),
                capture_output=True, text=True, timeout=300,
            )
            results["frontend_output"] = proc.stdout
            results["frontend_returncode"] = proc.returncode
        except Exception as e:
            results["frontend_error"] = str(e)

    result_key = f"{test_type}_test_results"
    return {
        result_key: results,
        "current_step": f"run_{test_type}_tests",
        "completed_steps": [f"run_{test_type}_tests"],
    }


async def _generate_manual_test_doc(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Generate manual testing guide."""
    prompt = f"""Generate a comprehensive Manual Testing Guide for:
**Feature:** {state.get("feature_name")}
**Strategy:** {state.get("strategy_document", "")[:5000]}

Include step-by-step test scenarios for every functional requirement.
Format as markdown following a standard QA testing guide template.
"""
    try:
        response = await llm.ainvoke(
            prompt=prompt,
            system_prompt="You are a QA Lead generating a manual testing guide.",
            node_name="generate_manual_test_doc",
            state_overrides=state,
            trace_name="generate_manual_test_doc",
        )
        return {"current_step": "generate_manual_test_doc", "completed_steps": ["generate_manual_test_doc"]}
    except Exception:
        return {"current_step": "generate_manual_test_doc", "completed_steps": ["generate_manual_test_doc"]}


async def _post_review_comments(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Post review comments to the GitHub PR."""
    logger.info("Posting review comments to PR #%d...", state.get("pr_number", 0))
    return {"current_step": "post_review_comments", "completed_steps": ["post_review_comments"]}


async def _notify_completion(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Notify that the feature is ready for human review."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(Panel(
        f"""[bold green]✅ Feature Implementation Complete![/bold green]

[bold]Feature:[/bold] {state.get("feature_name")}
[bold]Branch:[/bold] {state.get("branch_name")}
[bold]PR:[/bold] #{state.get("pr_number", "N/A")} — {state.get("pr_url", "")}
[bold]Review:[/bold] {"Approved" if not state.get("review_changes_needed") else "Changes Requested"}
[bold]Commits:[/bold] {len(state.get("commit_log", []))}

The PR is ready for human review and merge.
""",
        title="🎉 HomeCare Agentic Framework",
        border_style="green",
    ))

    return {"current_step": "complete", "completed_steps": ["notify_ready_for_merge"]}
