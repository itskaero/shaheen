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
_REDACTED = "[REDACTED]"


class _SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if _TOKEN_LIKE.search(message):
            record.msg = _TOKEN_LIKE.sub(_REDACTED, message)
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
