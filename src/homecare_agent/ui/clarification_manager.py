# Author: C A B M
# Date: 2026-09-17

"""Asynchronous Clarification Manager for coordinating human-in-the-loop Q&A.

Bridges LangGraph execution running in the background with the Gradio Web UI,
allowing the agent to pause at ask_clarifications, present questions on the
Clarification tab, and unblock once the user submits answers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ClarificationSession:
    """State and async future for a single feature intake clarification run."""

    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self.questions: list[dict[str, Any]] = []
        self.answer_future: asyncio.Future[str] | None = None
        self.answers: list[dict[str, Any]] = []
        self.is_waiting = False


class ClarificationManager:
    """Thread-safe manager for active clarification sessions keyed by trace_id."""

    _instance: ClarificationManager | None = None

    def __init__(self) -> None:
        self._sessions: dict[str, ClarificationSession] = {}
        self._latest_trace_id: str | None = None

    @classmethod
    def get_instance(cls) -> ClarificationManager:
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = ClarificationManager()
        return cls._instance

    def register_session(self, trace_id: str) -> ClarificationSession:
        """Register a new pipeline run session for interactive clarifications."""
        session = ClarificationSession(trace_id)
        self._sessions[trace_id] = session
        self._latest_trace_id = trace_id
        logger.info("[ClarificationManager] Registered session for trace_id=%s", trace_id)
        return session

    def has_session(self, trace_id: str | None) -> bool:
        """Check if an active web session exists for this trace ID."""
        if not trace_id:
            return bool(self._latest_trace_id and self._latest_trace_id in self._sessions)
        return trace_id in self._sessions

    def get_session(self, trace_id: str | None = None) -> ClarificationSession | None:
        """Get session by trace ID, falling back to the latest active trace ID."""
        if trace_id and trace_id in self._sessions:
            return self._sessions[trace_id]
        if self._latest_trace_id and self._latest_trace_id in self._sessions:
            return self._sessions[self._latest_trace_id]
        return None

    def request_clarification(
        self,
        trace_id: str,
        questions: list[dict[str, Any]],
    ) -> asyncio.Future[str]:
        """Record questions and create the future to wait for user answer."""
        session = self._sessions.get(trace_id)
        if not session:
            session = self.register_session(trace_id)

        session.questions = questions
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        session.answer_future = loop.create_future()
        session.is_waiting = True
        logger.info(
            "[ClarificationManager] Posed %d questions for trace_id=%s; awaiting user answer",
            len(questions),
            trace_id,
        )
        return session.answer_future

    async def wait_for_answer(
        self,
        trace_id: str,
        timeout: float = 600.0,
    ) -> str:
        """Asynchronously wait for the user to submit clarification answers."""
        session = self.get_session(trace_id)
        if not session or not session.answer_future:
            logger.warning("[ClarificationManager] No pending answer future for trace_id=%s", trace_id)
            return ""

        try:
            answer = await asyncio.wait_for(session.answer_future, timeout=timeout)
            logger.info("[ClarificationManager] Received answer for trace_id=%s: %s", trace_id, answer[:80])
            return answer
        except asyncio.TimeoutError:
            logger.warning("[ClarificationManager] Timed out waiting for clarification answer for trace_id=%s", trace_id)
            return ""
        finally:
            session.is_waiting = False

    def submit_answer(self, answer_text: str, trace_id: str | None = None) -> bool:
        """Submit user answer, resolving the waiting future and unblocking the graph."""
        session = self.get_session(trace_id)
        if not session:
            logger.warning("[ClarificationManager] Submit attempted with no active session (trace_id=%s)", trace_id)
            return False

        if session.answer_future and not session.answer_future.done():
            session.answer_future.set_result(answer_text)
            session.is_waiting = False
            logger.info("[ClarificationManager] Successfully submitted answer for trace_id=%s", session.trace_id)
            return True

        logger.warning("[ClarificationManager] Session was not waiting for an answer (trace_id=%s)", session.trace_id)
        return False

    def clear_session(self, trace_id: str) -> None:
        """Remove completed session."""
        self._sessions.pop(trace_id, None)
        if self._latest_trace_id == trace_id:
            self._latest_trace_id = None
