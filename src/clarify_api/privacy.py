"""Privacy-safe logging helpers for the API."""

from __future__ import annotations

import logging
import re

_BINARY_RE = re.compile(r"""b['"].*['"]""")
_SENSITIVE_KEYS = ("file", "bytes", "summary", "text", "image")


class PrivacyFilter(logging.Filter):
    """Drop log records that look like request bodies or field dumps."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return False
        if _BINARY_RE.search(msg):
            return False
        lower = msg.lower()
        for key in _SENSITIVE_KEYS:
            if f"{key}=" in lower or f'"{key}"' in lower or f"'{key}'" in lower:
                return False
        return True


def get_privacy_logger(name: str = "clarify_api") -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, PrivacyFilter) for f in logger.filters):
        logger.addFilter(PrivacyFilter())
    return logger


def log_explain_event(
    logger: logging.Logger,
    *,
    error: str | None,
    latency_ms: float,
    card_type: str | None,
) -> None:
    """Log only allowed explain metrics — never request bodies or field values."""
    logger.info(
        "explain error=%s latency_ms=%.1f card_type=%s",
        error,
        latency_ms,
        card_type,
    )
