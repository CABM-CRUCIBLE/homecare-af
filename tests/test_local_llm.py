# Author: C A B M
# Date: 2026-09-17

"""Tests for locally hosted LLM support and multi-endpoint routing."""

import pytest

from homecare_agent.config import Settings
from homecare_agent.llm.provider import LLMProvider


def test_default_openrouter_routing_when_local_disabled():
    """Verify that when local_llm_enabled is False, all nodes use OpenRouter models."""
    settings = Settings(
        openrouter_api_key="test-key",
        openrouter_model="anthropic/claude-sonnet-4",
        model_architecture="anthropic/claude-opus-4",
        model_code="deepseek/deepseek-coder",
        local_llm_enabled=False,
    )
    provider = LLMProvider(settings)

    # Architecture node routes to cloud model
    arch_llm, arch_model = provider.resolve_llm_and_model_for_node("generate_strategy")
    assert arch_model == "anthropic/claude-opus-4"
    assert arch_llm.openai_api_base == "https://openrouter.ai/api/v1"

    # Code node routes to OpenRouter code model
    code_llm, code_model = provider.resolve_llm_and_model_for_node("execute_wave")
    assert code_model == "deepseek/deepseek-coder"
    assert code_llm.openai_api_base == "https://openrouter.ai/api/v1"


def test_hybrid_routing_with_local_llm_for_code():
    """Verify hybrid mode: cloud for architecture, local LLM for code generation."""
    settings = Settings(
        openrouter_api_key="test-key",
        model_architecture="anthropic/claude-opus-4",
        model_review="anthropic/claude-sonnet-4",
        local_llm_enabled=True,
        local_llm_for_code=True,
        local_llm_base_url="http://localhost:11434/v1",
        local_llm_code_model="qwen2.5-coder:32b",
        local_llm_api_key="ollama",
    )
    provider = LLMProvider(settings)

    # Architecture node stays on OpenRouter
    arch_llm, arch_model = provider.resolve_llm_and_model_for_node("generate_strategy")
    assert arch_model == "anthropic/claude-opus-4"
    assert arch_llm.openai_api_base == "https://openrouter.ai/api/v1"

    # Reviewer node stays on OpenRouter
    review_llm, review_model = provider.resolve_llm_and_model_for_node("review_architecture")
    assert review_model == "anthropic/claude-sonnet-4"
    assert review_llm.openai_api_base == "https://openrouter.ai/api/v1"

    # Code generation nodes route to local LLM (Ollama)
    code_llm, code_model = provider.resolve_llm_and_model_for_node("execute_wave")
    assert code_model == "qwen2.5-coder:32b"
    assert code_llm.openai_api_base == "http://localhost:11434/v1"
    assert code_llm.openai_api_key.get_secret_value() == "ollama"

    # Fix application node also routes to local LLM
    fix_llm, fix_model = provider.resolve_llm_and_model_for_node("apply_review_fixes")
    assert fix_model == "qwen2.5-coder:32b"
    assert fix_llm.openai_api_base == "http://localhost:11434/v1"


def test_multi_endpoint_model_cache():
    """Verify provider cache separates models by endpoint without collisions."""
    settings = Settings(
        openrouter_api_key="test-key",
        openrouter_base_url="https://openrouter.ai/api/v1",
        local_llm_enabled=True,
        local_llm_base_url="http://localhost:8000/v1",
        local_llm_code_model="deepseek-coder:33b",
    )
    provider = LLMProvider(settings)

    cloud_client = provider.get_llm("deepseek-coder:33b")
    local_client = provider.get_llm("deepseek-coder:33b", base_url="http://localhost:8000/v1")

    assert cloud_client.openai_api_base == "https://openrouter.ai/api/v1"
    assert local_client.openai_api_base == "http://localhost:8000/v1"

    # Caching preserves separate instances
    assert "deepseek-coder:33b@https://openrouter.ai/api/v1" in provider._model_cache
    assert "deepseek-coder:33b@http://localhost:8000/v1" in provider._model_cache
    assert cloud_client is not local_client


def test_state_overrides_for_local_llm():
    """Verify runtime state overrides can specify custom local model and URL."""
    settings = Settings(
        openrouter_api_key="test-key",
        local_llm_enabled=True,
        local_llm_for_code=True,
        local_llm_base_url="http://localhost:11434/v1",
        local_llm_code_model="default-local:7b",
    )
    provider = LLMProvider(settings)

    state_override = {
        "local_llm_code_model": "custom-vllm-model:70b",
        "local_llm_base_url": "http://192.168.1.100:8000/v1",
    }
    llm, model = provider.resolve_llm_and_model_for_node("execute_wave", state_overrides=state_override)

    assert model == "custom-vllm-model:70b"
    assert llm.openai_api_base == "http://192.168.1.100:8000/v1"


def test_is_code_node_helper():
    """Verify is_code_node categorization."""
    settings = Settings(openrouter_api_key="test-key")
    assert settings.is_code_node("execute_wave") is True
    assert settings.is_code_node("write_files") is True
    assert settings.is_code_node("apply_review_fixes") is True
    assert settings.is_code_node("run_unit_tests") is True

    assert settings.is_code_node("intake_feature") is False
    assert settings.is_code_node("generate_strategy") is False
    assert settings.is_code_node("review_architecture") is False
