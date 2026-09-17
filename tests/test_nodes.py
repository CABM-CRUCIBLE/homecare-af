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


@pytest.mark.asyncio
async def test_intake_feature_error_handling_with_trace_id(caplog):
    import logging
    caplog.set_level(logging.INFO)

    settings = Settings(openrouter_api_key="mock-key")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Simulated LLM network timeout"))

    test_trace_id = "0123456789abcdef0123456789abcdef"
    state: AgentState = {
        "trace_id": test_trace_id,
        "feature_name": "Error Intake Test",
        "feature_description": "Testing error behavior",
    }

    result = await intake_feature(state, settings, mock_llm)

    assert result["current_step"] == "intake_feature"
    assert "errors" in result
    assert len(result["errors"]) == 1
    assert result["errors"][0]["step"] == "intake_feature"
    assert result["errors"][0]["trace_id"] == test_trace_id
    assert "Simulated LLM network timeout" in result["errors"][0]["message"]

    # Check that start and error logs were emitted with trace_id
    log_records = caplog.text
    assert f"[START:intake_feature][trace_id={test_trace_id}]" in log_records
    assert f"[ERROR:intake_feature][trace_id={test_trace_id}]" in log_records


@pytest.mark.asyncio
async def test_generate_prompts_error_handling_with_trace_id(caplog):
    import logging
    caplog.set_level(logging.INFO)

    from homecare_agent.graph.nodes.generate_prompts import generate_agentic_prompts

    settings = Settings(openrouter_api_key="mock-key")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=ValueError("Failed to generate prompts"))

    test_trace_id = "fedcba9876543210fedcba9876543210"
    state: AgentState = {
        "trace_id": test_trace_id,
        "feature_name": "Work Package Test",
        "strategy_document": "Strategy details",
        "tactical_plan": "Tactical details",
    }

    result = await generate_agentic_prompts(state, settings, mock_llm)

    assert "errors" in result
    assert result["errors"][0]["step"] == "generate_agentic_prompts"
    assert result["errors"][0]["trace_id"] == test_trace_id

    log_records = caplog.text
    assert f"[START:generate_agentic_prompts][trace_id={test_trace_id}]" in log_records
    assert f"[ERROR:generate_agentic_prompts][trace_id={test_trace_id}]" in log_records


@pytest.mark.asyncio
async def test_review_architecture_logging_and_completion(caplog):
    import logging
    caplog.set_level(logging.INFO)

    from homecare_agent.graph.nodes.review_arch import review_architecture

    settings = Settings(openrouter_api_key="mock-key")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value="# Architecture Review: Approved\n\nVerdict: APPROVED\nScore: A+")

    test_trace_id = "aabbccddeeff00112233445566778899"
    state: AgentState = {
        "trace_id": test_trace_id,
        "feature_name": "Review Test Feature",
        "strategy_document": "Valid strategy",
        "tactical_plan": "Valid plan",
    }

    result = await review_architecture(state, settings, mock_llm)

    assert result["architecture_approved"] is True
    assert result["current_step"] == "review_architecture"

    log_records = caplog.text
    assert f"[START:review_architecture][trace_id={test_trace_id}]" in log_records
    assert f"[COMPLETED:review_architecture][trace_id={test_trace_id}]" in log_records


@pytest.mark.asyncio
async def test_code_review_error_handling_with_trace_id(caplog):
    import logging
    caplog.set_level(logging.INFO)

    from homecare_agent.graph.nodes.code_review import perform_code_review

    settings = Settings(openrouter_api_key="mock-key")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Code review service unavailable"))

    test_trace_id = "11223344556677889900aabbccddeeff"
    state: AgentState = {
        "trace_id": test_trace_id,
        "feature_name": "Code Review Failure Test",
        "generated_code": {"test.cs": "public class Test {}"},
    }

    result = await perform_code_review(state, settings, mock_llm)

    assert "errors" in result
    assert result["errors"][0]["step"] == "code_review"
    assert result["errors"][0]["trace_id"] == test_trace_id

    log_records = caplog.text
    assert f"[START:perform_code_review][trace_id={test_trace_id}]" in log_records
    assert f"[ERROR:perform_code_review][trace_id={test_trace_id}]" in log_records

