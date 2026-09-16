# Author: C A B M
# Date: 2026-09-17

"""OpenRouter LLM provider with Langfuse tracing integration.

Provides a unified interface to OpenRouter's API using LangChain's
ChatOpenAI with custom base URL. Supports vision models for wireframe
analysis and integrates with Langfuse for full observability of every
LLM call — token usage, latency, cost, and prompt/response pairs.
Enforces a single unified trace ID across the entire workflow run.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from typing import Any

from langchain_core.callbacks import CallbackManager
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from homecare_agent.config import Settings

logger = logging.getLogger(__name__)

_HEX_32_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def normalize_trace_id(trace_id: str | None) -> str:
    """Ensure trace_id conforms to the OpenTelemetry / Langfuse 32-character hex format.

    Args:
        trace_id: Candidate trace ID (can be UUID, hex string, or slug).

    Returns:
        A valid 32-character lowercase hex trace ID.
    """
    if not trace_id:
        return uuid.uuid4().hex

    cleaned = str(trace_id).replace("-", "").strip().lower()
    if _HEX_32_PATTERN.match(cleaned):
        return cleaned

    # Deterministically hash non-conforming IDs to a valid 32-char hex string
    return hashlib.md5(cleaned.encode("utf-8")).hexdigest()


class LLMProvider:
    """OpenRouter BYOK LLM provider with optional Langfuse tracing.

    Usage:
        settings = get_settings()
        provider = LLMProvider(settings)
        provider.set_workflow_trace("my-trace-id")
        response = await provider.ainvoke("Generate a strategy document...")
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._callback_manager: CallbackManager | None = None
        self._langfuse_client: Any = None
        self._langfuse_handler: Any = None
        self._active_handlers: dict[str, Any] = {}
        self._workflow_trace_id: str | None = None
        self._workflow_trace_name: str = ""

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
        """Initialize Langfuse client and default callback handler."""
        try:
            from langfuse import Langfuse

            self._langfuse_client = Langfuse(
                public_key=self._settings.langfuse_public_key,
                secret_key=self._settings.langfuse_secret_key,
                host=self._settings.langfuse_host,
            )

            try:
                from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
            except ImportError:
                from langfuse.callback import CallbackHandler as LangfuseCallbackHandler  # type: ignore[no-redef]

            self._langfuse_handler = LangfuseCallbackHandler(
                public_key=self._settings.langfuse_public_key,
            )
            self._callback_manager = CallbackManager([self._langfuse_handler])
            logger.info("Langfuse tracing enabled at %s", self._settings.langfuse_host)
        except ImportError:
            logger.warning("langfuse package not installed; tracing disabled.")
        except Exception:
            logger.exception("Failed to initialize Langfuse; tracing disabled.")

    def set_workflow_trace(self, trace_id: str | None, trace_name: str = "") -> str | None:
        """Set the active single trace ID for the entire workflow run.

        All subsequent LLM invocations and node executions will attach to this trace ID.

        Args:
            trace_id: The unique trace identifier for the run.
            trace_name: Optional descriptive label (e.g., feature name).

        Returns:
            The normalized 32-character hex trace ID.
        """
        if trace_id:
            self._workflow_trace_id = normalize_trace_id(trace_id)
        else:
            self._workflow_trace_id = None
        self._workflow_trace_name = trace_name
        logger.info("Workflow trace ID set to: %s (name=%s)", self._workflow_trace_id, trace_name or "workflow")
        return self._workflow_trace_id

    @property
    def workflow_trace_id(self) -> str | None:
        """The active workflow trace ID."""
        return self._workflow_trace_id

    def get_langfuse_handler(self, trace_id: str | None = None) -> Any:
        """Get or create a Langfuse callback handler bound to a specific trace ID.

        Ensures all calls using this handler nest into the designated parent trace.

        Args:
            trace_id: Trace ID to bind to. Falls back to workflow_trace_id.

        Returns:
            A configured Langfuse CallbackHandler, or None if Langfuse is disabled.
        """
        if not self._settings.langfuse_enabled:
            return None

        effective_id = trace_id or self._workflow_trace_id
        if not effective_id:
            return self._langfuse_handler

        norm_id = normalize_trace_id(effective_id)
        if norm_id not in self._active_handlers:
            try:
                try:
                    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
                except ImportError:
                    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler  # type: ignore[no-redef]

                handler = LangfuseCallbackHandler(
                    public_key=self._settings.langfuse_public_key,
                    trace_context={"trace_id": norm_id},
                )
                self._active_handlers[norm_id] = handler
            except Exception:
                logger.exception("Failed to create LangfuseCallbackHandler for trace %s", norm_id)
                return self._langfuse_handler

        return self._active_handlers[norm_id]

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
        """The default Langfuse callback handler, if enabled."""
        return self._langfuse_handler

    @property
    def langfuse_client(self) -> Any:
        """The Langfuse client instance, if enabled."""
        return self._langfuse_client

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
        trace_id: str = "",
    ) -> str:
        """Invoke the LLM asynchronously with automatic per-node model routing and trace binding.

        Args:
            prompt: The user/instruction prompt.
            system_prompt: Optional system prompt prepended.
            node_name: LangGraph node name to determine the model automatically.
            model_override: Explicit override model for this call.
            state_overrides: Optional state containing model configurations and trace_id.
            trace_name: Langfuse trace name / span name for this invocation.
            trace_metadata: Additional metadata for Langfuse tracing.
            trace_id: Explicit trace ID override (falls back to state or workflow trace ID).

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

        # Resolve single unified trace ID
        target_trace_id = (
            trace_id
            or (state_overrides.get("trace_id") if state_overrides else "")
            or self._workflow_trace_id
            or ""
        )
        if target_trace_id:
            target_trace_id = normalize_trace_id(target_trace_id)

        # Configure Langfuse tracing
        kwargs: dict[str, Any] = {}
        metadata = dict(trace_metadata or {})
        metadata["effective_model"] = effective_model
        if node_name:
            metadata["node_name"] = node_name
        if target_trace_id:
            metadata["workflow_trace_id"] = target_trace_id

        handler = self.get_langfuse_handler(target_trace_id)
        if handler:
            run_name = trace_name or (f"node_{node_name}" if node_name else "homecare_llm")
            kwargs["config"] = {
                "callbacks": [handler],
                "run_name": run_name,
                "metadata": metadata,
            }

        logger.debug(
            "Invoking node '%s' with model '%s' (trace_id=%s)",
            node_name or "(default)",
            effective_model,
            target_trace_id or "none",
        )
        response = await llm.ainvoke(messages, **kwargs)
        return str(response.content)

    async def ainvoke_with_vision(
        self,
        prompt: str,
        image_urls: list[str],
        *,
        system_prompt: str = "",
        trace_name: str = "",
        trace_id: str = "",
        node_name: str = "",
        state_overrides: dict[str, Any] | None = None,
        trace_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Invoke the vision LLM with image inputs and unified trace binding.

        Args:
            prompt: The text instruction alongside the images.
            image_urls: List of image URLs (can be data: URIs for local files).
            system_prompt: Optional system prompt.
            trace_name: Langfuse trace name.
            trace_id: Explicit trace ID override.
            node_name: LangGraph node name.
            state_overrides: Optional state containing trace_id.
            trace_metadata: Additional metadata for Langfuse.

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
                path = Path(url_or_path)
                if path.exists():
                    data = base64.b64encode(path.read_bytes()).decode()
                    suffix = path.suffix.lstrip(".").lower()
                    mime = {
                        "png": "image/png",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "webp": "image/webp",
                        "gif": "image/gif",
                    }.get(suffix, "image/png")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{data}"},
                    })
                else:
                    logger.warning("Image file not found: %s", url_or_path)

        messages.append(HumanMessage(content=content))

        # Resolve single unified trace ID
        target_trace_id = (
            trace_id
            or (state_overrides.get("trace_id") if state_overrides else "")
            or self._workflow_trace_id
            or ""
        )
        if target_trace_id:
            target_trace_id = normalize_trace_id(target_trace_id)

        kwargs: dict[str, Any] = {}
        handler = self.get_langfuse_handler(target_trace_id)
        if handler:
            metadata = dict(trace_metadata or {})
            metadata["vision"] = True
            if node_name:
                metadata["node_name"] = node_name
            if target_trace_id:
                metadata["workflow_trace_id"] = target_trace_id

            kwargs["config"] = {
                "callbacks": [handler],
                "run_name": trace_name or "vision_analysis",
                "metadata": metadata,
            }

        response = await self._vision_llm.ainvoke(messages, **kwargs)
        return str(response.content)

    def invoke_sync(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        trace_name: str = "",
        trace_id: str = "",
        trace_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Synchronous invocation for CLI and non-async contexts.

        Args:
            prompt: The user/instruction prompt.
            system_prompt: Optional system prompt.
            trace_name: Langfuse trace name.
            trace_id: Explicit trace ID override.
            trace_metadata: Additional metadata for Langfuse.

        Returns:
            The LLM response text.
        """
        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        target_trace_id = trace_id or self._workflow_trace_id or ""
        if target_trace_id:
            target_trace_id = normalize_trace_id(target_trace_id)

        kwargs: dict[str, Any] = {}
        handler = self.get_langfuse_handler(target_trace_id)
        if handler:
            metadata = dict(trace_metadata or {})
            if target_trace_id:
                metadata["workflow_trace_id"] = target_trace_id
            kwargs["config"] = {
                "callbacks": [handler],
                "run_name": trace_name or "llm_sync",
                "metadata": metadata,
            }

        response = self._llm.invoke(messages, **kwargs)
        return str(response.content)

    def flush_langfuse(self) -> None:
        """Flush pending Langfuse events from client and all active trace handlers."""
        if self._langfuse_client:
            try:
                self._langfuse_client.flush()
                logger.info("Langfuse client events flushed.")
            except Exception:
                logger.exception("Failed to flush Langfuse client events.")

        for tid, handler in list(self._active_handlers.items()):
            try:
                if hasattr(handler, "flush"):
                    handler.flush()
            except Exception:
                logger.debug("Failed to flush handler for trace %s", tid)

        if self._langfuse_handler and hasattr(self._langfuse_handler, "flush"):
            try:
                self._langfuse_handler.flush()
            except Exception:
                pass
