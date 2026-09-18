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

import asyncio
import hashlib
import logging
import re
import threading
import uuid
from typing import Any

from langchain_core.callbacks import CallbackManager
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from homecare_agent.config import Settings
from homecare_agent.security.redaction import redact_secrets

logger = logging.getLogger(__name__)

_HEX_32_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class InsufficientCreditsError(Exception):
    """Raised when OpenRouter API key has exhausted credits (HTTP 402)."""

    pass


class LLMBudgetExceededError(Exception):
    """Raised when workflow exceeds maximum permitted LLM calls per run."""

    pass


def _is_credit_exhaustion_error(exc: Exception) -> bool:
    """Check if exception represents credit exhaustion or payment required."""
    err_str = str(exc).lower()
    status_code = getattr(exc, "status_code", None)
    if not status_code and hasattr(exc, "response"):
        status_code = getattr(exc.response, "status_code", None)
    if status_code == 402:
        return True
    keywords = [
        "insufficient_credits",
        "insufficient credits",
        "payment required",
        "out of credits",
        "credit balance is too low",
        "exceeded your current quota",
        "402",
    ]
    return any(kw in err_str for kw in keywords)


def _is_retryable_error(exc: Exception) -> bool:
    """Check if exception is a transient error eligible for retry."""
    err_str = str(exc).lower()
    status_code = getattr(exc, "status_code", None)
    if not status_code and hasattr(exc, "response"):
        status_code = getattr(exc.response, "status_code", None)
    if status_code in (429, 502, 503, 504):
        return True
    retry_keywords = [
        "rate limit",
        "too many requests",
        "connection reset",
        "service unavailable",
        "gateway timeout",
        "bad gateway",
    ]
    return any(kw in err_str for kw in retry_keywords)


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

    # Deterministically hash non-conforming IDs to a valid 32-char hex string using SHA-256
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:32]



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
        self._call_count = 0
        self._budget_lock = asyncio.Lock()
        self._sync_budget_lock = threading.Lock()
        self._semaphore = asyncio.Semaphore(max(1, settings.max_parallel_workers))

        # Primary LLM (text generation)
        self._llm = self.get_llm(settings.openrouter_model or "anthropic/claude-sonnet-4")

        # Vision LLM (wireframe analysis)
        self._vision_llm = self.get_llm(settings.effective_vision_model or "anthropic/claude-sonnet-4")

        logger.info(
            "LLM Provider initialized — arch_model=%s, code_model=%s, vision=%s, langfuse=%s, max_calls=%d, max_workers=%d",
            settings.model_architecture or settings.openrouter_model or "(default)",
            settings.model_code or "(default)",
            settings.effective_vision_model or "(default)",
            settings.langfuse_enabled,
            settings.max_llm_calls_per_run,
            settings.max_parallel_workers,
        )

    @property
    def call_count(self) -> int:
        """Total number of LLM invocations executed across this provider instance."""
        with self._sync_budget_lock:
            return self._call_count

    def set_call_count(self, count: int) -> None:
        """Set the current LLM call count (STATE-02), e.g. when resuming from checkpoint."""
        with self._sync_budget_lock:
            self._call_count = max(0, count)
            logger.info("Restored LLM call count to %d", self._call_count)

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

            setup_kwargs: dict[str, Any] = {
                "public_key": self._settings.langfuse_public_key,
                "secret_key": self._settings.langfuse_secret_key,
                "host": self._settings.langfuse_host,
            }
            try:
                import inspect
                sig = inspect.signature(LangfuseCallbackHandler.__init__)
                has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                if not has_kwargs:
                    setup_kwargs = {k: v for k, v in setup_kwargs.items() if k in sig.parameters}
            except Exception:
                pass

            self._langfuse_handler = LangfuseCallbackHandler(**setup_kwargs)
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

                handler_kwargs: dict[str, Any] = {
                    "public_key": self._settings.langfuse_public_key,
                    "secret_key": self._settings.langfuse_secret_key,
                    "host": self._settings.langfuse_host,
                    "trace_context": {"trace_id": norm_id},
                }

                try:
                    import inspect
                    sig = inspect.signature(LangfuseCallbackHandler.__init__)
                    has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                    if not has_kwargs:
                        handler_kwargs = {k: v for k, v in handler_kwargs.items() if k in sig.parameters}
                        if "stateful_client" in sig.parameters and self._langfuse_client:
                            try:
                                handler_kwargs["stateful_client"] = self._langfuse_client.trace(
                                    id=norm_id,
                                    name=self._workflow_trace_name or f"workflow_{norm_id[:8]}",
                                )
                            except Exception:
                                pass
                        elif "session_id" in sig.parameters and "session_id" not in handler_kwargs:
                            handler_kwargs["session_id"] = norm_id
                except Exception:
                    pass

                handler = LangfuseCallbackHandler(**handler_kwargs)
                self._active_handlers[norm_id] = handler
            except Exception:
                logger.exception("Failed to create LangfuseCallbackHandler for trace %s", norm_id)
                return self._langfuse_handler

        return self._active_handlers[norm_id]

    def flush(self) -> None:
        """Flush any pending Langfuse events and active handlers."""
        if self._langfuse_client and hasattr(self._langfuse_client, "flush"):
            try:
                self._langfuse_client.flush()
            except Exception:
                pass
        for handler in list(self._active_handlers.values()):
            if hasattr(handler, "flush"):
                try:
                    handler.flush()
                except Exception:
                    pass
        if self._langfuse_handler and hasattr(self._langfuse_handler, "flush"):
            try:
                self._langfuse_handler.flush()
            except Exception:
                pass

    def _create_llm(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> ChatOpenAI:
        """Create a ChatOpenAI instance pointed at OpenRouter or a local OpenAI-compatible server.

        Args:
            model: The model identifier (OpenRouter slug or local model name).
            base_url: Optional API base URL override (e.g. local endpoint).
            api_key: Optional API key override.
            timeout: Optional HTTP request timeout in seconds.

        Returns:
            A configured ChatOpenAI instance.
        """
        effective_base_url = (base_url or self._settings.openrouter_base_url).strip()
        effective_api_key = (api_key or self._settings.openrouter_api_key).strip()

        # OpenAI SDK v3 (langchain-openai ≥ 1.4) moved custom HTTP headers from
        # model_kwargs["headers"] to the dedicated default_headers= constructor
        # parameter.  Passing them via model_kwargs causes:
        #   TypeError: AsyncCompletions.create() got an unexpected keyword argument 'headers'
        kwargs: dict[str, Any] = {
            "openai_api_key": effective_api_key,
            "openai_api_base": effective_base_url,
            "model": model,
            "max_tokens": self._settings.max_tokens,
            "temperature": self._settings.temperature,
            "request_timeout": timeout or 300.0,
            "default_headers": {
                "HTTP-Referer": "https://homecare-agent.local",
                "X-Title": "HomeCare Agentic Framework",
            },
        }
        return ChatOpenAI(**kwargs)

    def get_llm(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> ChatOpenAI:
        """Get or create a cached ChatOpenAI instance for the given model identifier and endpoint (LLM-02)."""
        clean_model = model.strip() or self._settings.openrouter_model or "anthropic/claude-sonnet-4"
        effective_base_url = (base_url or self._settings.openrouter_base_url).strip()
        cache_key = f"{clean_model}@{effective_base_url}"

        if cache_key in self._model_cache:
            return self._model_cache[cache_key]
        if clean_model in self._model_cache:
            return self._model_cache[clean_model]

        self._model_cache[cache_key] = self._create_llm(
            clean_model,
            base_url=effective_base_url,
            api_key=api_key,
            timeout=timeout,
        )
        return self._model_cache[cache_key]

    def get_llm_for_node(
        self,
        node_name: str,
        model_override: str = "",
        state_overrides: dict[str, Any] | None = None,
    ) -> ChatOpenAI:
        """Resolve and return the ChatOpenAI instance assigned to a specific LangGraph node."""
        llm, _ = self.resolve_llm_and_model_for_node(node_name, model_override, state_overrides)
        return llm

    def resolve_llm_and_model_for_node(
        self,
        node_name: str,
        model_override: str = "",
        state_overrides: dict[str, Any] | None = None,
    ) -> tuple[ChatOpenAI, str]:
        """Resolve and return the ChatOpenAI instance and model name assigned to a specific LangGraph node."""
        overrides = state_overrides or {}
        if model_override:
            return self.get_llm(model_override), model_override

        # Check local LLM routing for code generation nodes
        if (
            self._settings.local_llm_enabled
            and self._settings.local_llm_for_code
            and self._settings.is_code_node(node_name)
        ):
            local_model = (
                overrides.get("local_llm_code_model")
                or self._settings.local_llm_code_model
            )
            local_url = (
                overrides.get("local_llm_base_url")
                or self._settings.local_llm_base_url
            )
            local_key = (
                overrides.get("local_llm_api_key")
                or self._settings.local_llm_api_key
            )
            timeout = self._settings.local_llm_timeout
            logger.info(
                "[ROUTING:LocalLLM] Routing code node '%s' to local LLM: model='%s', url='%s'",
                node_name,
                local_model,
                local_url,
            )
            llm = self.get_llm(local_model, base_url=local_url, api_key=local_key, timeout=timeout)
            return llm, local_model

        # Standard OpenRouter model routing
        model = self._settings.get_model_for_node(node_name, state_overrides)
        return self.get_llm(model), model

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

    def _check_and_increment_budget_sync(self) -> None:
        """Check and increment the LLM call budget synchronously under thread lock (LLM-01)."""
        with self._sync_budget_lock:
            if self._call_count >= self._settings.max_llm_calls_per_run:
                raise LLMBudgetExceededError(
                    f"Global LLM call limit reached ({self._call_count}/{self._settings.max_llm_calls_per_run}). "
                    "Halting run to prevent runaway API spend."
                )
            self._call_count += 1

    async def _check_and_increment_budget_async(self) -> None:
        """Check and increment the LLM call budget under an async lock."""
        async with self._budget_lock:
            self._check_and_increment_budget_sync()

    async def _execute_with_retry_async(
        self,
        llm: ChatOpenAI,
        messages: list[BaseMessage],
        kwargs: dict[str, Any],
        *,
        node_name: str,
        effective_model: str,
        target_trace_id: str,
    ) -> str:
        """Execute an async LLM call with retry, budget checking, and concurrency control."""
        async with self._semaphore:
            await self._check_and_increment_budget_async()
            max_retries = max(1, self._settings.max_retries)
            last_exception: Exception | None = None

            for attempt in range(1, max_retries + 1):
                try:
                    response = await llm.ainvoke(messages, **kwargs)
                    return str(response.content)
                except Exception as e:
                    last_exception = e
                    if _is_credit_exhaustion_error(e):
                        logger.critical(
                            "[CRITICAL:LLMProvider][trace_id=%s] Credit exhaustion detected (HTTP 402/insufficient credits): %s. "
                            "Immediate fail-fast triggered to prevent retries.",
                            target_trace_id or "none",
                            e,
                        )
                        raise InsufficientCreditsError(
                            f"OpenRouter API key has insufficient credits: {e}"
                        ) from e

                    if _is_retryable_error(e) and attempt < max_retries:
                        backoff = (2 ** attempt) + 0.5
                        logger.warning(
                            "[WARN:LLMProvider][trace_id=%s] Transient error on attempt %d/%d for node '%s': %s. Backing off for %.1fs...",
                            target_trace_id or "none",
                            attempt,
                            max_retries,
                            node_name or "(default)",
                            e,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue

                    logger.error(
                        "[ERROR:LLMProvider][trace_id=%s] LLM ainvoke failed on attempt %d/%d for node '%s' (model: %s): %s",
                        target_trace_id or "none",
                        attempt,
                        max_retries,
                        node_name or "(default)",
                        effective_model,
                        e,
                        exc_info=True,
                    )
                    raise

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state: LLM invocation exited without response or exception.")

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
            llm, effective_model = self.resolve_llm_and_model_for_node(
                node_name, state_overrides=state_overrides
            )
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
        metadata = {
            k: (redact_secrets(v) if isinstance(v, str) else v)
            for k, v in (trace_metadata or {}).items()
        }
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

        return await self._execute_with_retry_async(
            llm,
            messages,
            kwargs,
            node_name=node_name or "(default)",
            effective_model=effective_model,
            target_trace_id=target_trace_id,
        )

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
            if url_or_path.startswith("data:"):
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url_or_path},
                })
            elif url_or_path.startswith(("http://", "https://")):
                # Pre-fetch image URL to base64 data URI to guarantee delivery across all vision providers
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                        resp = await client.get(url_or_path)
                        if resp.status_code == 200:
                            b64_data = base64.b64encode(resp.content).decode()
                            raw_ctype = resp.headers.get("content-type", "image/png").split(";")[0].strip()
                            ctype = raw_ctype if raw_ctype.startswith("image/") else "image/png"
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{ctype};base64,{b64_data}"},
                            })
                            logger.info("Successfully pre-fetched image URL %s (%d bytes)", url_or_path, len(resp.content))
                        else:
                            logger.warning("Image URL %s returned status %d; passing raw URL", url_or_path, resp.status_code)
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": url_or_path},
                            })
                except Exception as fetch_err:
                    logger.warning("Could not pre-fetch image URL %s (%s); passing direct URL", url_or_path, fetch_err)
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
            metadata = {
                k: (redact_secrets(v) if isinstance(v, str) else v)
                for k, v in (trace_metadata or {}).items()
            }
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

        effective_model = self._settings.effective_vision_model or "anthropic/claude-sonnet-4"

        return await self._execute_with_retry_async(
            self._vision_llm,
            messages,
            kwargs,
            node_name=node_name or "vision",
            effective_model=effective_model,
            target_trace_id=target_trace_id,
        )

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
            metadata = {
                k: (redact_secrets(v) if isinstance(v, str) else v)
                for k, v in (trace_metadata or {}).items()
            }
            if target_trace_id:
                metadata["workflow_trace_id"] = target_trace_id
            kwargs["config"] = {
                "callbacks": [handler],
                "run_name": trace_name or "llm_sync",
                "metadata": metadata,
            }

        self._check_and_increment_budget_sync()

        try:
            response = self._llm.invoke(messages, **kwargs)
            return str(response.content)
        except Exception as e:
            if _is_credit_exhaustion_error(e):
                logger.critical(
                    "[CRITICAL:LLMProvider][trace_id=%s] Credit exhaustion detected in sync invoke: %s.",
                    target_trace_id or "none",
                    e,
                )
                raise InsufficientCreditsError(
                    f"OpenRouter API key has insufficient credits: {e}"
                ) from e
            logger.error(
                "[ERROR:LLMProvider][trace_id=%s] Sync LLM invoke failed: %s",
                target_trace_id or "none",
                e,
                exc_info=True,
            )
            raise

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
