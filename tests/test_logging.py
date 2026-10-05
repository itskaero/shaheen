"""Log redaction (docs/DECISIONS.md ADR-123)."""

from __future__ import annotations

import logging

from core.logging import configure_logging, redact


def test_the_brawlhalla_api_key_never_reaches_the_log() -> None:
    line = (
        "HTTP Request: GET https://api.brawlhalla.com/player/1/ranked?api_key=SECRETKEY123 "
        '"HTTP/1.1 200 OK"'
    )
    cleaned = redact(line)
    assert "SECRETKEY123" not in cleaned
    assert "api_key=[REDACTED]" in cleaned
    assert cleaned.endswith('"HTTP/1.1 200 OK"')
    assert redact("&API_KEY=abc&page=2") == "&API_KEY=[REDACTED]&page=2"


def test_request_urls_are_not_logged_at_info() -> None:
    configure_logging("INFO")
    assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)
    assert logging.getLogger("httpx").isEnabledFor(logging.WARNING)
