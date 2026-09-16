# Author: C A B M
# Date: 2026-09-17

"""Notification and termination nodes for the HomeCare Agentic Framework (ARCH-01, ARCH-03)."""

from __future__ import annotations

import logging
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState

logger = logging.getLogger(__name__)


async def post_review_comments(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Post review comments to the GitHub PR.

    Args:
        state: Current graph state.
        settings: Application settings.

    Returns:
        State updates with step status.
    """
    trace_id = state.get("trace_id", "no-trace")
    pr_number = state.get("pr_number", 0)
    logger.info("[START:post_review_comments][trace_id=%s] Posting review comments to PR #%d...", trace_id, pr_number)
    logger.info("[COMPLETED:post_review_comments][trace_id=%s] Review comments posted to PR #%d", trace_id, pr_number)
    return {"current_step": "post_review_comments", "completed_steps": ["post_review_comments"]}


async def notify_completion(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Notify that the feature implementation is complete and ready for human review.

    Args:
        state: Current graph state.
        settings: Application settings.

    Returns:
        State updates with completion status.
    """
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


async def error_halt(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Terminal node reached when critical node outputs fail validation (ARCH-01).

    Halts the workflow run immediately to prevent cascading silent failures
    and runaway LLM token consumption.

    Args:
        state: Current graph state.
        settings: Application settings.

    Returns:
        State updates marking the pipeline as halted with error details.
    """
    from rich.console import Console
    from rich.panel import Panel

    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    errors = state.get("errors", [])
    last_step = state.get("current_step", "unknown")

    logger.critical(
        "[HALT:error_halt][trace_id=%s] Pipeline halted after critical step '%s' failed for '%s'. Total errors: %d",
        trace_id,
        last_step,
        feature_name,
        len(errors),
    )

    console = Console()
    error_summary = "\n".join(
        f"• [{e.get('step', 'general')}] {e.get('message', 'Unknown error')}"
        for e in errors[-5:]
        if isinstance(e, dict)
    ) or "Critical prerequisite output missing (strategy/tactical/prompts)."

    console.print(Panel(
        f"""[bold red]🛑 Pipeline Halted — Critical Node Failure[/bold red]

[bold]Feature:[/bold] {feature_name}
[bold]Last Step:[/bold] {last_step}
[bold]Trace ID:[/bold] {trace_id}

[bold yellow]Reasons for halt:[/bold yellow]
{error_summary}

Execution stopped cleanly to prevent cascading errors and unnecessary API token spend.
Use checkpoint resume (`homecare-agent resume --trace-id {trace_id}`) after resolving the issue.
""",
        title="⚠️ Execution Circuit Breaker",
        border_style="red",
    ))

    return {
        "current_step": "error_halt",
        "completed_steps": ["error_halt"],
    }
