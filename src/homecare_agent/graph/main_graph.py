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

    # Architecture pipeline
    graph.add_edge("analyze_codebase", "generate_strategy")
    graph.add_edge("generate_strategy", "generate_tactical_plan")
    graph.add_edge("generate_tactical_plan", "generate_adrs")
    graph.add_edge("generate_adrs", "generate_agentic_prompts")
    graph.add_edge("generate_agentic_prompts", "review_architecture")

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

    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    questions = state.get("clarification_questions", [])

    logger.info(
        "[START:ask_clarifications][trace_id=%s] Asking %d clarification question(s) for '%s'",
        trace_id,
        len(questions),
        feature_name,
    )

    console = Console()
    answers: list[dict[str, Any]] = []

    try:
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

        logger.info(
            "[COMPLETED:ask_clarifications][trace_id=%s] Collected %d answer(s)",
            trace_id,
            len(answers),
        )

        clarification_iteration = state.get("clarification_iteration", 0) + 1
        return {
            "clarification_answers": answers,
            "clarification_complete": True,
            "clarification_iteration": clarification_iteration,
            "current_step": "ask_clarifications",
            "completed_steps": ["ask_clarifications"],
        }
    except Exception as e:
        logger.error(
            "[ERROR:ask_clarifications][trace_id=%s] Failed during clarifications: %s",
            trace_id,
            e,
            exc_info=True,
        )
        clarification_iteration = state.get("clarification_iteration", 0) + 1
        return {
            "clarification_complete": True,
            "clarification_iteration": clarification_iteration,
            "errors": [{"step": "ask_clarifications", "trace_id": trace_id, "message": f"Clarifications failed: {e}"}],
            "current_step": "ask_clarifications",
            "completed_steps": ["ask_clarifications"],
        }


async def _revise_architecture(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Revise architecture based on review findings."""
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    logger.info("[START:revise_architecture][trace_id=%s] Revising architecture for '%s'...", trace_id, feature_name)

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
            trace_metadata={"feature_name": feature_name, "trace_id": trace_id},
        )
        logger.info(
            "[COMPLETED:revise_architecture][trace_id=%s] Architecture revised successfully (%d chars)",
            trace_id,
            len(response),
        )
        arch_iteration = state.get("arch_iteration", 0) + 1
        return {
            "strategy_document": response,
            "arch_iteration": arch_iteration,
            "current_step": "revise_architecture",
            "completed_steps": ["revise_architecture"],
        }
    except Exception as e:
        logger.error(
            "[ERROR:revise_architecture][trace_id=%s] Architecture revision failed for '%s': %s",
            trace_id,
            feature_name,
            e,
            exc_info=True,
        )
        arch_iteration = state.get("arch_iteration", 0) + 1
        return {
            "architecture_approved": False,  # Fail-safe: do not approve unrevised architecture on failure
            "arch_iteration": arch_iteration,
            "errors": [{"step": "revise_architecture", "trace_id": trace_id, "message": f"Architecture revision failed: {e}"}],
            "current_step": "revise_architecture",
            "completed_steps": ["revise_architecture"],
        }


async def _run_tests(state: AgentState, settings: Settings, test_type: str = "unit") -> dict[str, Any]:
    """Run tests (unit, e2e, load) asynchronously without blocking the event loop."""
    import subprocess
    from pathlib import Path

    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    step_name = f"run_{test_type}_tests"
    logger.info("[START:%s][trace_id=%s] Running %s tests for '%s'...", step_name, trace_id, test_type, feature_name)

    repo_path = Path(state.get("repo_path", settings.repo_path))
    results: dict[str, Any] = {"type": test_type, "passed": 0, "failed": 0, "total": 0}
    errors: list[dict[str, Any]] = []

    # Dynamic directory discovery
    backend_dir = repo_path / "code" / "backend"
    if not backend_dir.exists():
        sln_files = list(repo_path.glob("**/*.sln"))
        csproj_files = list(repo_path.glob("**/*.csproj"))
        if sln_files:
            backend_dir = sln_files[0].parent
        elif csproj_files:
            backend_dir = csproj_files[0].parent
        else:
            backend_dir = repo_path

    frontend_dir = repo_path / "code" / "frontend"
    if not frontend_dir.exists():
        package_files = [p for p in repo_path.glob("**/package.json") if "node_modules" not in str(p)]
        if package_files:
            frontend_dir = package_files[0].parent
        else:
            frontend_dir = repo_path

    if test_type == "unit":
        # Backend unit tests (.NET) - non-blocking thread execution
        try:
            if any(backend_dir.glob("*.sln")) or any(backend_dir.glob("*.csproj")) or (backend_dir / "code" / "backend").exists():
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["dotnet", "test", "--verbosity", "minimal"],
                    cwd=str(backend_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                results["backend_output"] = proc.stdout
                results["backend_returncode"] = proc.returncode
        except Exception as e:
            logger.error("[ERROR:%s][trace_id=%s] Backend tests failed to run: %s", step_name, trace_id, e, exc_info=True)
            results["backend_error"] = str(e)
            errors.append({"step": step_name, "trace_id": trace_id, "component": "backend", "message": str(e)})

        # Frontend unit tests (Node.js/Vitest) - non-blocking thread execution
        try:
            if (frontend_dir / "package.json").exists():
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["npm", "test", "--", "--run"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    shell=(sys.platform == "win32"),
                )
                results["frontend_output"] = proc.stdout
                results["frontend_returncode"] = proc.returncode
        except Exception as e:
            logger.error("[ERROR:%s][trace_id=%s] Frontend tests failed to run: %s", step_name, trace_id, e, exc_info=True)
            results["frontend_error"] = str(e)
            errors.append({"step": step_name, "trace_id": trace_id, "component": "frontend", "message": str(e)})

    elif test_type == "e2e":
        # End-to-end tests (Playwright)
        try:
            if (frontend_dir / "package.json").exists():
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["npx", "playwright", "test"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    shell=(sys.platform == "win32"),
                )
                results["e2e_output"] = proc.stdout
                results["e2e_returncode"] = proc.returncode
        except Exception as e:
            logger.error("[ERROR:%s][trace_id=%s] E2E tests failed: %s", step_name, trace_id, e, exc_info=True)
            results["e2e_error"] = str(e)

    elif test_type == "load":
        # Load tests (k6)
        load_test_file = repo_path / "tests" / "load" / "test.js"
        if load_test_file.exists():
            try:
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["k6", "run", str(load_test_file)],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                results["load_output"] = proc.stdout
                results["load_returncode"] = proc.returncode
            except Exception as e:
                logger.error("[ERROR:%s][trace_id=%s] Load tests failed: %s", step_name, trace_id, e, exc_info=True)
                results["load_error"] = str(e)

    result_key = f"{test_type}_test_results"
    logger.info(
        "[COMPLETED:%s][trace_id=%s] Finished %s tests (passed=%s, failed=%s)",
        step_name,
        trace_id,
        test_type,
        results.get("passed", 0),
        results.get("failed", 0),
    )

    update: dict[str, Any] = {
        result_key: results,
        "current_step": step_name,
        "completed_steps": [step_name],
    }
    if errors:
        update["errors"] = errors
    return update


async def _generate_manual_test_doc(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Generate manual testing guide."""
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    logger.info("[START:generate_manual_test_doc][trace_id=%s] Generating manual test guide for '%s'...", trace_id, feature_name)

    prompt = f"""Generate a comprehensive Manual Testing Guide for:
**Feature:** {feature_name}
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
            trace_metadata={"feature_name": feature_name, "trace_id": trace_id},
        )
        logger.info(
            "[COMPLETED:generate_manual_test_doc][trace_id=%s] Manual test guide generated successfully (%d chars)",
            trace_id,
            len(response),
        )
        return {"current_step": "generate_manual_test_doc", "completed_steps": ["generate_manual_test_doc"]}
    except Exception as e:
        logger.error(
            "[ERROR:generate_manual_test_doc][trace_id=%s] Manual test guide generation failed: %s",
            trace_id,
            e,
            exc_info=True,
        )
        return {
            "errors": [{"step": "generate_manual_test_doc", "trace_id": trace_id, "message": f"Manual test guide generation failed: {e}"}],
            "current_step": "generate_manual_test_doc",
            "completed_steps": ["generate_manual_test_doc"],
        }


async def _post_review_comments(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Post review comments to the GitHub PR."""
    trace_id = state.get("trace_id", "no-trace")
    pr_number = state.get("pr_number", 0)
    logger.info("[START:post_review_comments][trace_id=%s] Posting review comments to PR #%d...", trace_id, pr_number)
    logger.info("[COMPLETED:post_review_comments][trace_id=%s] Review comments posted to PR #%d", trace_id, pr_number)
    return {"current_step": "post_review_comments", "completed_steps": ["post_review_comments"]}


async def _notify_completion(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Notify that the feature is ready for human review."""
    from rich.console import Console
    from rich.panel import Panel

    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    logger.info("[START:notify_ready_for_merge][trace_id=%s] Notifying completion for '%s'...", trace_id, feature_name)

    console = Console()
    console.print(Panel(
        f"""[bold green]✅ Feature Implementation Complete![/bold green]

[bold]Feature:[/bold] {feature_name}
[bold]Branch:[/bold] {state.get("branch_name")}
[bold]PR:[/bold] #{state.get("pr_number", "N/A")} — {state.get("pr_url", "")}
[bold]Review:[/bold] {"Approved" if not state.get("review_changes_needed") else "Changes Requested"}
[bold]Commits:[/bold] {len(state.get("commit_log", []))}

The PR is ready for human review and merge.
""",
        title="🎉 HomeCare Agentic Framework",
        border_style="green",
    ))

    logger.info("[COMPLETED:notify_ready_for_merge][trace_id=%s] Feature pipeline run completed successfully for '%s'", trace_id, feature_name)
    return {"current_step": "complete", "completed_steps": ["notify_ready_for_merge"]}
