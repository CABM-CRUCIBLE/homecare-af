# Author: C A B M
# Date: 2026-09-17

"""Documentation generation node for manual QA testing guides (ARCH-03)."""

from __future__ import annotations

import logging
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


async def generate_manual_test_doc(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Generate manual testing guide for QA teams.

    Args:
        state: Current graph state.
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        State updates containing documentation status.
    """
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
