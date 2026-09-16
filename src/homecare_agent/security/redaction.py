# Author: C A B M
# Date: 2026-09-17

"""Security module for masking sensitive secrets, tokens, and credentials in logs and traces."""

from __future__ import annotations

import logging
import re
from typing import Any

REDACTION_PATTERNS = [
    # OpenRouter API Key
    (re.compile(r"sk-or-v1-[a-f0-9]{10}[a-f0-9]+"), "sk-or-v1-***REDACTED***"),
    # Anthropic API Key
    (re.compile(r"sk-ant-[a-zA-Z0-9_\-]{8}[a-zA-Z0-9_\-]+"), "sk-ant-***REDACTED***"),
    # Generic sk- API keys
    (re.compile(r"sk-[a-zA-Z0-9]{8}[a-zA-Z0-9]{12,}"), "sk-***REDACTED***"),
    # GitHub Personal Access Token
    (re.compile(r"ghp_[a-zA-Z0-9]{8}[a-zA-Z0-9]+"), "ghp_***REDACTED***"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{8}[a-zA-Z0-9_]+"), "github_pat_***REDACTED***"),
    # Authorization header Bearer tokens
    (re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9\-._~+/]{15,}={0,2}"), "Bearer ***REDACTED***"),
    # Database connection string passwords (e.g., postgresql://user:pass@host)
    (re.compile(r"(postgres(?:ql)?:\/\/[^:]+:)([^@]+)(@)"), r"\1***REDACTED***\3"),
    # Cryptographic Private Keys
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[PRIVATE KEY REDACTED]"),
]


def redact_secrets(text: str) -> str:
    """Mask known credentials, API keys, and connection strings from text.

    Args:
        text: Candidate string containing potential sensitive data.

    Returns:
        Sanitized string with sensitive tokens replaced with redaction placeholders.
    """
    if not text:
        return text

    sanitized = text
    for pattern, replacement in REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class SecretMaskingFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials from all log records before output."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize log record message and arguments."""
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (redact_secrets(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_secrets(a) if isinstance(a, str) else a
                    for a in record.args
                )

        return True
