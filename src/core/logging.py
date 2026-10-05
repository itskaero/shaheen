"""Logging configuration.

Per docs/DEVELOPMENT.md: log setup start/end, important setup changes, API
failures, command failures and scheduled jobs. Never log secrets. The
_SecretRedactionFilter is a defense-in-depth backstop in case a secret ever
ends up interpolated into a log message.
"""

from __future__ import annotations

import logging
import re

_TOKEN_LIKE = re.compile(r"[\w-]{20,}\.[\w-]{6,}\.[\w-]{20,}")  # discord token shape
# The Brawlhalla API takes its key as a query parameter, so any logged
# request URL carries it (ADR-123).
_API_KEY_PARAM = re.compile(r"(api_key=)[^&\s\"']+", re.IGNORECASE)
_REDACTED = "[REDACTED]"


def redact(message: str) -> str:
    message = _TOKEN_LIKE.sub(_REDACTED, message)
    return _API_KEY_PARAM.sub(lambda m: m.group(1) + _REDACTED, message)


class _SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, at process startup."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    handler.addFilter(_SecretRedactionFilter())

    root.handlers.clear()
    root.addHandler(handler)

    # discord.py is chatty at INFO; keep it visible but not overwhelming.
    logging.getLogger("discord").setLevel(max(root.level, logging.INFO))
    # httpx logs every request URL at INFO, and Brawlhalla's carry the API
    # key. The client logs its own failures, so only warnings are kept.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(max(root.level, logging.WARNING))
