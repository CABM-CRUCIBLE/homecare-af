# Author: C A B M
# Date: 2026-09-17

"""Tests for safety guardrails: credit exhaustion, retry backoff, budget ceiling, and loop limits."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.edges.routing import arch_approved, needs_clarification
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import (
    InsufficientCreditsError,
    LLMBudgetExceededError,
    LLMProvider,
    _is_credit_exhaustion_error,
    _is_retryable_error,
)


def test_credit_exhaustion_detection():
    """Verify error detection for credit exhaustion keywords and status codes."""
    exc1 = Exception("402 Payment Required: insufficient_credits")
    assert _is_credit_exhaustion_error(exc1) is True

    exc2 = Exception("Your credit balance is too low to access the OpenRouter API.")
    assert _is_credit_exhaustion_error(exc2) is True

    exc3 = Exception("404 Not Found")
    assert _is_credit_exhaustion_error(exc3) is False

    mock_resp = MagicMock(status_code=402)
    exc4 = Exception("Payment failure")
    exc4.response = mock_resp
    assert _is_credit_exhaustion_error(exc4) is True


def test_retryable_error_detection():
    """Verify error detection for transient/retryable errors."""
    exc1 = Exception("429 Too Many Requests: rate limit exceeded")
    assert _is_retryable_error(exc1) is True

    exc2 = Exception("503 Service Unavailable: connection reset")
    assert _is_retryable_error(exc2) is True

    exc3 = Exception("401 Unauthorized")
    assert _is_retryable_error(exc3) is False


@pytest.mark.asyncio
async def test_insufficient_credits_fail_fast():
    """Verify HTTP 402/insufficient credits raises InsufficientCreditsError immediately without retrying."""
    settings = Settings(
        openrouter_api_key="sk-test",
        max_retries=3,
        max_llm_calls_per_run=10,
    )
    provider = LLMProvider(settings)

    mock_chat = MagicMock()
    mock_chat.ainvoke = AsyncMock(side_effect=Exception("402 Payment Required: insufficient_credits"))
    provider._llm = mock_chat
    provider.get_llm = MagicMock(return_value=mock_chat)

    with pytest.raises(InsufficientCreditsError):
        await provider.ainvoke("Generate code")

    # Verify it failed fast on attempt 1 without exhausting all 3 retries
    assert mock_chat.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_llm_budget_ceiling():
    """Verify LLMBudgetExceededError trips when max_llm_calls_per_run is reached."""
    settings = Settings(
        openrouter_api_key="sk-test",
        max_retries=1,
        max_llm_calls_per_run=2,
    )
    provider = LLMProvider(settings)

    mock_chat = MagicMock()
    mock_chat.ainvoke = AsyncMock(return_value=MagicMock(content="Response"))
    provider._llm = mock_chat
    provider.get_llm = MagicMock(return_value=mock_chat)

    # Call 1: OK
    res1 = await provider.ainvoke("Prompt 1")
    assert res1 == "Response"
    assert provider.call_count == 1

    # Call 2: OK
    res2 = await provider.ainvoke("Prompt 2")
    assert res2 == "Response"
    assert provider.call_count == 2

    # Call 3: Budget exceeded!
    with pytest.raises(LLMBudgetExceededError) as exc_info:
        await provider.ainvoke("Prompt 3")

    assert "Global LLM call limit reached (2/2)" in str(exc_info.value)
    assert mock_chat.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_retry_on_transient_rate_limit():
    """Verify transient 429 rate limit error is retried and succeeds on subsequent attempt."""
    settings = Settings(
        openrouter_api_key="sk-test",
        max_retries=3,
        max_llm_calls_per_run=10,
    )
    provider = LLMProvider(settings)

    mock_chat = MagicMock()
    # Fail first call with 429, succeed on second call
    mock_chat.ainvoke = AsyncMock(
        side_effect=[
            Exception("429 Too Many Requests: rate limit"),
            MagicMock(content="Recovered Response"),
        ]
    )
    provider._llm = mock_chat
    provider.get_llm = MagicMock(return_value=mock_chat)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        res = await provider.ainvoke("Test prompt")

    assert res == "Recovered Response"
    assert mock_chat.ainvoke.call_count == 2
    assert mock_sleep.call_count == 1


def test_arch_iteration_guardrail():
    """Verify arch_approved cuts off runaway loops when max_arch_iterations is reached."""
    settings = Settings(openrouter_api_key="sk-test", max_arch_iterations=3)

    # Within limit: route to revise
    state_under: AgentState = {
        "architecture_approved": False,
        "arch_iteration": 2,
    }
    assert arch_approved(state_under, settings) == "revise_architecture"

    # At or above limit: force create_branch to halt loop
    state_limit: AgentState = {
        "architecture_approved": False,
        "arch_iteration": 3,
    }
    assert arch_approved(state_limit, settings) == "create_branch"


def test_clarification_iteration_guardrail():
    """Verify needs_clarification cuts off infinite questions when max_clarification_iterations is reached."""
    settings = Settings(openrouter_api_key="sk-test", max_clarification_iterations=2)

    # Within limit: route to ask_clarifications
    state_under: AgentState = {
        "clarification_complete": False,
        "clarification_iteration": 1,
    }
    assert needs_clarification(state_under, settings) == "ask_clarifications"

    # At or above limit: force analyze_codebase
    state_limit: AgentState = {
        "clarification_complete": False,
        "clarification_iteration": 2,
    }
    assert needs_clarification(state_limit, settings) == "analyze_codebase"
