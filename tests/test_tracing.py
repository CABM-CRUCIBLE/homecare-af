# Author: C A B M
# Date: 2026-09-17

"""Tests for unified workflow trace ID and Langfuse tracing integration."""

from __future__ import annotations

import re
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider, normalize_trace_id


def test_normalize_trace_id_valid_32_hex() -> None:
    """A valid 32-char lowercase hex ID should be returned as-is."""
    valid_id = "0123456789abcdef0123456789abcdef"
    assert normalize_trace_id(valid_id) == valid_id


def test_normalize_trace_id_uuid_with_hyphens() -> None:
    """A standard UUID with hyphens should have hyphens stripped into 32 hex chars."""
    raw_uuid = str(uuid.uuid4())
    normalized = normalize_trace_id(raw_uuid)
    assert len(normalized) == 32
    assert re.match(r"^[0-9a-f]{32}$", normalized)
    assert normalized == raw_uuid.replace("-", "").lower()


def test_normalize_trace_id_arbitrary_string() -> None:
    """Arbitrary strings should be deterministically hashed into 32 hex chars."""
    slug = "my-custom-feature-run"
    normalized = normalize_trace_id(slug)
    assert len(normalized) == 32
    assert re.match(r"^[0-9a-f]{32}$", normalized)
    # Deterministic
    assert normalize_trace_id(slug) == normalized


def test_normalize_trace_id_empty_or_none() -> None:
    """Empty or None input should generate a fresh valid 32 hex trace ID."""
    t1 = normalize_trace_id(None)
    t2 = normalize_trace_id("")
    assert len(t1) == 32
    assert len(t2) == 32
    assert re.match(r"^[0-9a-f]{32}$", t1)
    assert re.match(r"^[0-9a-f]{32}$", t2)


def test_agent_state_has_trace_id() -> None:
    """Verify that AgentState TypedDict contains trace_id."""
    state: AgentState = {
        "trace_id": "0123456789abcdef0123456789abcdef",
        "feature_name": "Test Feature",
        "feature_description": "Testing trace ID",
    }
    assert state["trace_id"] == "0123456789abcdef0123456789abcdef"


def test_llm_provider_workflow_trace_id() -> None:
    """Verify LLMProvider.set_workflow_trace sets normalized trace ID."""
    settings = Settings(
        openrouter_api_key="sk-test",
        langfuse_enabled=False,
    )
    provider = LLMProvider(settings)
    assert provider.workflow_trace_id is None

    test_id = "abcdef0123456789abcdef0123456789"
    norm = provider.set_workflow_trace(test_id, trace_name="Test Run")
    assert norm == test_id
    assert provider.workflow_trace_id == test_id

    # Reset
    provider.set_workflow_trace(None)
    assert provider.workflow_trace_id is None


def test_llm_provider_get_langfuse_handler_when_disabled() -> None:
    """When Langfuse is disabled, get_langfuse_handler returns None."""
    settings = Settings(
        openrouter_api_key="sk-test",
        langfuse_enabled=False,
    )
    provider = LLMProvider(settings)
    assert provider.get_langfuse_handler() is None
    assert provider.get_langfuse_handler("0123456789abcdef0123456789abcdef") is None


def test_llm_provider_get_langfuse_handler_when_enabled() -> None:
    """When Langfuse is enabled, get_langfuse_handler creates and caches handlers bound to trace_id."""
    settings = Settings(
        openrouter_api_key="sk-test",
        langfuse_enabled=True,
        langfuse_public_key="pk-lf-test",
        langfuse_secret_key="sk-lf-test",
        langfuse_host="http://localhost:13000",
    )
    with patch("langfuse.Langfuse"), patch("langfuse.langchain.CallbackHandler") as mock_handler_cls:
        mock_instance = MagicMock()
        mock_handler_cls.return_value = mock_instance

        provider = LLMProvider(settings)
        trace_id = "0123456789abcdef0123456789abcdef"
        provider.set_workflow_trace(trace_id)

        handler = provider.get_langfuse_handler()
        assert handler == mock_instance
        mock_handler_cls.assert_called_with(
            public_key="pk-lf-test",
            secret_key="sk-lf-test",
            host="http://localhost:13000",
            trace_context={"trace_id": trace_id},
        )

        # Calling again with same trace ID returns cached instance
        handler2 = provider.get_langfuse_handler(trace_id)
        assert handler2 == mock_instance
        assert mock_handler_cls.call_count == 2  # 1 for default handler during setup + 1 for trace_context


@pytest.mark.asyncio
async def test_ainvoke_attaches_trace_id_metadata() -> None:
    """Verify that ainvoke attaches trace_id to metadata and passes callback config."""
    settings = Settings(
        openrouter_api_key="sk-test",
        langfuse_enabled=True,
        langfuse_public_key="pk-lf-test",
        langfuse_secret_key="sk-lf-test",
        langfuse_host="http://localhost:13000",
    )

    with patch("langfuse.Langfuse"), patch("langfuse.langchain.CallbackHandler") as mock_handler_cls:
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler

        provider = LLMProvider(settings)
        workflow_trace = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        provider.set_workflow_trace(workflow_trace)

        # Mock the underlying ChatOpenAI client
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Generated text"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        provider._llm = mock_llm
        provider._model_cache["anthropic/claude-sonnet-4"] = mock_llm
        provider._model_cache[f"anthropic/claude-sonnet-4@{settings.openrouter_base_url}"] = mock_llm

        # Call with state containing same workflow trace
        state: AgentState = {
            "trace_id": workflow_trace,
            "feature_name": "Test Feature",
        }
        resp = await provider.ainvoke(
            "Hello test",
            node_name="test_node",
            state_overrides=state,
        )

        assert resp == "Generated text"
        assert mock_llm.ainvoke.called
        call_kwargs = mock_llm.ainvoke.call_args[1]

        assert "config" in call_kwargs
        config = call_kwargs["config"]
        assert config["callbacks"] == [mock_handler]
        assert config["metadata"]["workflow_trace_id"] == workflow_trace
        assert config["metadata"]["node_name"] == "test_node"


def test_settings_langfuse_init_credentials() -> None:
    """Verify that Settings includes default credentials for Langfuse auto-provisioning."""
    settings = Settings()
    assert settings.langfuse_init_project_id == "homecare"
    assert settings.langfuse_init_user_email == "admin@homecare.local"
    assert isinstance(settings.langfuse_init_user_password, str)
