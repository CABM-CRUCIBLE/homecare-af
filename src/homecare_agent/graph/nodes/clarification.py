# Author: C A B M
# Date: 2026-09-17

"""Clarification node for the HomeCare Agentic Framework (ARCH-03)."""

from __future__ import annotations

import logging
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


async def ask_clarifications(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Present clarification questions to the user via CLI or web UI.

    In CLI mode: uses Rich prompts for interactive Q&A.
    In Web mode: records questions for Gradio interface.

    Args:
        state: Current graph state.
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        State updates containing user answers and clarification status.
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
