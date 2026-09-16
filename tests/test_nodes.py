# Author: C A B M
# Date: 2026-09-17

"""Unit tests for LangGraph nodes with mock LLM provider."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.nodes.intake import intake_feature
from homecare_agent.graph.state import AgentState


@pytest.mark.asyncio
async def test_intake_feature_with_clarifications():
    settings = Settings(openrouter_api_key="mock-key")
    mock_llm = MagicMock()

    json_response = """\
{
  "functional_requirements": [{"id": "FR-01", "title": "Create Order"}],
  "non_functional_requirements": [{"id": "NFR-01", "category": "Security"}],
  "constraints": ["Clean Architecture"],
  "assumptions": ["Tenant header provided"],
  "out_of_scope": [],
  "clarification_needed": true,
  "clarification_questions": [
    {"id": "q1", "category": "business_logic", "question": "What is the timeout?"}
  ],
  "integration_points": ["Orders", "Vendors"],
  "compliance_implications": ["HIPAA"]
}
"""
    mock_llm.ainvoke = AsyncMock(return_value=json_response)

    state: AgentState = {
        "feature_name": "Order Management",
        "feature_description": "Create and track vendor orders",
        "wireframe_paths": [],
    }

    result = await intake_feature(state, settings, mock_llm)

    assert result["current_step"] == "intake_feature"
    assert result["clarification_complete"] is False
    assert len(result["clarification_questions"]) == 1
    assert result["clarification_questions"][0]["id"] == "q1"


@pytest.mark.asyncio
async def test_intake_feature_without_clarifications():
    settings = Settings(openrouter_api_key="mock-key")
    mock_llm = MagicMock()

    json_response = """\
{
  "functional_requirements": [{"id": "FR-01", "title": "Create Order"}],
  "non_functional_requirements": [],
  "constraints": [],
  "assumptions": [],
  "out_of_scope": [],
  "clarification_needed": false,
  "clarification_questions": [],
  "integration_points": [],
  "compliance_implications": []
}
"""
    mock_llm.ainvoke = AsyncMock(return_value=json_response)

    state: AgentState = {
        "feature_name": "Order Management",
        "feature_description": "Well specified requirements",
    }

    result = await intake_feature(state, settings, mock_llm)

    assert result["clarification_complete"] is True
    assert len(result["clarification_questions"]) == 0
