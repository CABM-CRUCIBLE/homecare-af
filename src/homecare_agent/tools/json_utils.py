# Author: C A B M
# Date: 2026-09-17

"""Robust JSON parsing utilities for LLM output extraction (CODEGEN-01).

Handles markdown code fences (```json ... ```), preamble commentary,
escaped braces, and trailing commas commonly produced by LLMs.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_MARKDOWN_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def extract_json(text: str, default: Any = None) -> Any:
    """Extract and parse JSON from an LLM response string with fence stripping.

    Handles:
    1. Direct JSON string
    2. Markdown fenced code blocks: ```json ... ``` or ``` ... ```
    3. JSON embedded within conversational text
    4. Trailing commas produced by LLMs

    Args:
        text: The raw text response from the LLM.
        default: Fallback value to return if extraction or parsing fails.

    Returns:
        The parsed JSON data (dict, list, or primitive), or `default` on failure.
    """
    if not text or not isinstance(text, str):
        return default

    clean_text = text.strip()

    # 1. Check if enclosed in markdown code fences
    fence_matches = _MARKDOWN_CODE_BLOCK_RE.findall(clean_text)
    candidates: list[str] = []
    if fence_matches:
        candidates.extend(match.strip() for match in fence_matches if match.strip())

    # 2. Add whole text as candidate
    candidates.append(clean_text)

    # 3. Add slice between outermost { } or [ ]
    first_brace = clean_text.find("{")
    last_brace = clean_text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(clean_text[first_brace : last_brace + 1])

    first_bracket = clean_text.find("[")
    last_bracket = clean_text.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        candidates.append(clean_text[first_bracket : last_bracket + 1])

    # Try each candidate
    for candidate in candidates:
        # Try direct parse
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Try cleaning trailing commas
        cleaned_candidate = _TRAILING_COMMA_RE.sub(r"\1", candidate)
        try:
            return json.loads(cleaned_candidate)
        except json.JSONDecodeError:
            pass

    logger.warning("[JSON_UTILS:PARSE_FAIL] Could not extract valid JSON from response (length=%d)", len(text))
    return default
