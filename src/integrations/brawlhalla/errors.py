"""Brawlhalla API error types.

Kept distinct from core.exceptions.ShaheenError — callers (services) decide
how to translate these into user-safe messages (docs/COMMANDS.md: never
expose raw external API errors to users).
"""

from __future__ import annotations


class BrawlhallaAPIError(Exception):
    """Base class for all Brawlhalla API failures."""


class BrawlhallaUnauthorized(BrawlhallaAPIError):
    """401 — request was not made over HTTPS (should not happen in practice)."""


class BrawlhallaForbidden(BrawlhallaAPIError):
    """403 — missing or invalid API key."""


class BrawlhallaNotFound(BrawlhallaAPIError):
    """404 — the requested player/resource does not exist."""


class BrawlhallaRateLimited(BrawlhallaAPIError):
    """429 — the API key has hit its rate limit."""


class BrawlhallaServiceUnavailable(BrawlhallaAPIError):
    """503 — the Brawlhalla API is down for maintenance."""
