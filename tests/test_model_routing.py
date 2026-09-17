# Author: C A B M
# Date: 2026-09-17

"""Unit tests for multi-tier and per-node LLM model routing."""

from unittest.mock import MagicMock

import pytest

from homecare_agent.config import Settings
from homecare_agent.llm.provider import LLMProvider


def test_get_model_for_node_defaults():
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        openrouter_model="anthropic/claude-sonnet-4",
    )
    # Without tier overrides, all nodes fallback to openrouter_model
    assert settings.get_model_for_node("analyze_codebase") == "anthropic/claude-sonnet-4"
    assert settings.get_model_for_node("execute_wave") == "anthropic/claude-sonnet-4"
    assert settings.get_model_for_node("perform_code_review") == "anthropic/claude-sonnet-4"


def test_get_model_for_node_tier_routing():
    settings = Settings(
        openrouter_api_key="test-key",
        openrouter_model="anthropic/claude-sonnet-4",
        model_architecture="anthropic/claude-opus-4",
        model_code="deepseek/deepseek-coder",
        model_review="openai/gpt-4o",
    )

    # Architecture nodes should use model_architecture (high-reasoning / high-cost)
    assert settings.get_model_for_node("analyze_codebase") == "anthropic/claude-opus-4"
    assert settings.get_model_for_node("generate_strategy") == "anthropic/claude-opus-4"
    assert settings.get_model_for_node("generate_tactical_plan") == "anthropic/claude-opus-4"
    assert settings.get_model_for_node("generate_adrs") == "anthropic/claude-opus-4"

    # Code generation and test nodes should use model_code (medium / low-cost)
    assert settings.get_model_for_node("execute_wave") == "deepseek/deepseek-coder"
    assert settings.get_model_for_node("run_unit_tests") == "deepseek/deepseek-coder"
    assert settings.get_model_for_node("run_e2e_tests") == "deepseek/deepseek-coder"

    # Review nodes should use model_review
    assert settings.get_model_for_node("review_architecture") == "openai/gpt-4o"
    assert settings.get_model_for_node("perform_code_review") == "openai/gpt-4o"


def test_get_model_for_node_granular_node_models():
    settings = Settings(
        openrouter_api_key="test-key",
        model_architecture="anthropic/claude-sonnet-4",
        model_code="deepseek/deepseek-coder",
        node_models={
            "execute_wave": "meta-llama/llama-3.3-70b-instruct",
            "generate_adrs": "google/gemini-2.5-pro",
        },
    )

    # Granular node_models override the tier default
    assert settings.get_model_for_node("execute_wave") == "meta-llama/llama-3.3-70b-instruct"
    assert settings.get_model_for_node("generate_adrs") == "google/gemini-2.5-pro"

    # Other nodes keep their tier default
    assert settings.get_model_for_node("generate_strategy") == "anthropic/claude-sonnet-4"
    assert settings.get_model_for_node("run_unit_tests") == "deepseek/deepseek-coder"


def test_get_model_for_node_state_overrides():
    settings = Settings(
        openrouter_api_key="test-key",
        model_architecture="anthropic/claude-sonnet-4",
        model_code="deepseek/deepseek-coder",
    )

    state = {
        "model_code": "anthropic/claude-3.5-haiku",
        "node_models": {"execute_wave": "openai/gpt-4o-mini"},
    }

    # State overrides take precedence over settings
    assert settings.get_model_for_node("run_unit_tests", state_overrides=state) == "anthropic/claude-3.5-haiku"
    assert settings.get_model_for_node("execute_wave", state_overrides=state) == "openai/gpt-4o-mini"
    assert settings.get_model_for_node("generate_strategy", state_overrides=state) == "anthropic/claude-sonnet-4"


def test_llm_provider_model_caching():
    settings = Settings(
        openrouter_api_key="test-key",
        model_architecture="anthropic/claude-opus-4",
        model_code="deepseek/deepseek-coder",
    )
    provider = LLMProvider(settings)

    # Resolve models for different nodes
    arch_llm = provider.get_llm_for_node("generate_strategy")
    code_llm = provider.get_llm_for_node("execute_wave")

    # They should have different configured models
    assert arch_llm.model_name == "anthropic/claude-opus-4"
    assert code_llm.model_name == "deepseek/deepseek-coder"

    # Repeated calls should return the cached instance
    arch_llm_again = provider.get_llm_for_node("generate_strategy")
    assert arch_llm is arch_llm_again
