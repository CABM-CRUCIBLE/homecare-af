"""OpenRouter LLM provider with Langfuse tracing integration.

Provides a unified interface to OpenRouter's API using LangChain's
ChatOpenAI with custom base URL. Supports vision models for wireframe
analysis and integrates with Langfuse for full observability of every
LLM call — token usage, latency, cost, and prompt/response pairs.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import CallbackManager
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from homecare_agent.config import Settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """OpenRouter BYOK LLM provider with optional Langfuse tracing.

    Usage:
        settings = get_settings()
        provider = LLMProvider(settings)
        response = await provider.ainvoke("Generate a strategy document...")
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._callback_manager: CallbackManager | None = None
        self._langfuse_handler: Any = None

        # Initialize Langfuse if enabled
        if settings.langfuse_enabled:
            self._setup_langfuse()

        self._model_cache: dict[str, ChatOpenAI] = {}

        # Primary LLM (text generation)
        self._llm = self.get_llm(settings.openrouter_model or "anthropic/claude-sonnet-4")

        # Vision LLM (wireframe analysis)
        self._vision_llm = self.get_llm(settings.effective_vision_model or "anthropic/claude-sonnet-4")

        logger.info(
            "LLM Provider initialized — arch_model=%s, code_model=%s, vision=%s, langfuse=%s",
            settings.model_architecture or settings.openrouter_model or "(default)",
            settings.model_code or "(default)",
            settings.effective_vision_model or "(default)",
            settings.langfuse_enabled,
        )

    def _setup_langfuse(self) -> None:
        """Initialize Langfuse callback handler for LangChain tracing."""
        try:
            from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

            self._langfuse_handler = LangfuseCallbackHandler(
                public_key=self._settings.langfuse_public_key,
                secret_key=self._settings.langfuse_secret_key,
                host=self._settings.langfuse_host,
            )
            self._callback_manager = CallbackManager([self._langfuse_handler])
            logger.info("Langfuse tracing enabled at %s", self._settings.langfuse_host)
        except ImportError:
            logger.warning("langfuse package not installed; tracing disabled.")
        except Exception:
            logger.exception("Failed to initialize Langfuse; tracing disabled.")

    def _create_llm(self, model: str) -> ChatOpenAI:
        """Create a ChatOpenAI instance pointed at OpenRouter.

        Args:
            model: The OpenRouter model identifier.

        Returns:
            A configured ChatOpenAI instance.
        """
        kwargs: dict[str, Any] = {
            "openai_api_key": self._settings.openrouter_api_key,
            "openai_api_base": self._settings.openrouter_base_url,
            "model": model,
            "max_tokens": self._settings.max_tokens,
            "temperature": self._settings.temperature,
            "model_kwargs": {
                "headers": {
                    "HTTP-Referer": "https://homecare-agent.local",
                    "X-Title": "HomeCare Agentic Framework",
                },
            },
        }
        if self._callback_manager:
            kwargs["callback_manager"] = self._callback_manager
        return ChatOpenAI(**kwargs)

    def get_llm(self, model: str) -> ChatOpenAI:
        """Get or create a cached ChatOpenAI instance for the given model identifier."""
        clean_model = model.strip() or self._settings.openrouter_model or "anthropic/claude-sonnet-4"
        if clean_model not in self._model_cache:
            self._model_cache[clean_model] = self._create_llm(clean_model)
        return self._model_cache[clean_model]

    def get_llm_for_node(
        self,
        node_name: str,
        model_override: str = "",
        state_overrides: dict[str, Any] | None = None,
    ) -> ChatOpenAI:
        """Resolve and return the ChatOpenAI instance assigned to a specific LangGraph node."""
        if model_override:
            return self.get_llm(model_override)
        model = self._settings.get_model_for_node(node_name, state_overrides)
        return self.get_llm(model)

    @property
    def llm(self) -> ChatOpenAI:
        """The primary text-generation LLM."""
        return self._llm

    @property
    def vision_llm(self) -> ChatOpenAI:
        """The vision-capable LLM for wireframe/screenshot analysis."""
        return self._vision_llm

    @property
    def langfuse_handler(self) -> Any:
        """The Langfuse callback handler, if enabled."""
        return self._langfuse_handler

    async def ainvoke(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        node_name: str = "",
        model_override: str = "",
        state_overrides: dict[str, Any] | None = None,
        trace_name: str = "",
        trace_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Invoke the LLM asynchronously with automatic per-node model routing.

        Args:
            prompt: The user/instruction prompt.
            system_prompt: Optional system prompt prepended.
            node_name: LangGraph node name to determine the model automatically.
            model_override: Explicit override model for this call.
            state_overrides: Optional state containing model configurations.
            trace_name: Langfuse trace name for this invocation.
            trace_metadata: Additional metadata for Langfuse tracing.

        Returns:
            The LLM response text.
        """
        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # Determine effective model and client
        if model_override:
            effective_model = model_override
            llm = self.get_llm(model_override)
        elif node_name:
            effective_model = self._settings.get_model_for_node(node_name, state_overrides)
            llm = self.get_llm(effective_model)
        else:
            effective_model = self._settings.openrouter_model or "anthropic/claude-sonnet-4"
            llm = self._llm

        # Add Langfuse trace metadata
        kwargs: dict[str, Any] = {}
        metadata = dict(trace_metadata or {})
        metadata["effective_model"] = effective_model
        if node_name:
            metadata["node_name"] = node_name

        if self._langfuse_handler and (trace_name or node_name):
            kwargs["config"] = {
                "callbacks": [self._langfuse_handler],
                "run_name": trace_name or f"node_{node_name}",
                "metadata": metadata,
            }

        logger.debug("Invoking node '%s' with model '%s'", node_name or "(default)", effective_model)
        response = await llm.ainvoke(messages, **kwargs)
        return str(response.content)

    async def ainvoke_with_vision(
        self,
        prompt: str,
        image_urls: list[str],
        *,
        system_prompt: str = "",
        trace_name: str = "",
    ) -> str:
        """Invoke the vision LLM with image inputs.

        Args:
            prompt: The text instruction alongside the images.
            image_urls: List of image URLs (can be data: URIs for local files).
            system_prompt: Optional system prompt.
            trace_name: Langfuse trace name.

        Returns:
            The LLM response text.
        """
        import base64
        from pathlib import Path

        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # Build multimodal content
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for url_or_path in image_urls:
            if url_or_path.startswith(("http://", "https://", "data:")):
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url_or_path},
                })
            else:
                # Local file — encode as base64 data URI
                path = Path(url_or_path)
                if path.exists():
                    data = base64.b64encode(path.read_bytes()).decode()
                    suffix = path.suffix.lstrip(".").lower()
                    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}.get(suffix, "image/png")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{data}"},
                    })
                else:
                    logger.warning("Image file not found: %s", url_or_path)

        messages.append(HumanMessage(content=content))

        kwargs: dict[str, Any] = {}
        if self._langfuse_handler and trace_name:
            kwargs["config"] = {
                "callbacks": [self._langfuse_handler],
                "run_name": trace_name,
            }

        response = await self._vision_llm.ainvoke(messages, **kwargs)
        return str(response.content)

    def invoke_sync(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        trace_name: str = "",
    ) -> str:
        """Synchronous invocation for CLI and non-async contexts.

        Args:
            prompt: The user/instruction prompt.
            system_prompt: Optional system prompt.
            trace_name: Langfuse trace name.

        Returns:
            The LLM response text.
        """
        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        kwargs: dict[str, Any] = {}
        if self._langfuse_handler and trace_name:
            kwargs["config"] = {
                "callbacks": [self._langfuse_handler],
                "run_name": trace_name,
            }

        response = self._llm.invoke(messages, **kwargs)
        return str(response.content)

    def flush_langfuse(self) -> None:
        """Flush pending Langfuse events. Call before exit."""
        if self._langfuse_handler:
            try:
                self._langfuse_handler.flush()
                logger.info("Langfuse events flushed.")
            except Exception:
                logger.exception("Failed to flush Langfuse events.")
