"""Application-level exceptions.

Commands must never surface raw exception messages or external API errors to
users (docs/COMMANDS.md). Cogs should catch ShaheenError subclasses and show
a branded, user-safe message; unexpected exceptions should still be logged
with full detail server-side.
"""

from __future__ import annotations


class ShaheenError(Exception):
    """Base class for all expected, user-facing application errors."""


class ConfigurationError(ShaheenError):
    """Raised when required configuration is missing or invalid."""


class PermissionDeniedError(ShaheenError):
    """Raised when a user attempts an action they are not authorized for."""


class SetupError(ShaheenError):
    """Raised when the setup service cannot safely plan or apply changes."""


class NotFoundError(ShaheenError):
    """Raised when a requested player/member/resource does not exist."""


class IntegrationError(ShaheenError):
    """Raised when an external integration (e.g. Brawlhalla) fails.

    Services catch the integration's own exception types and re-raise this
    with a user-safe message — cogs never see the raw external error
    (docs/COMMANDS.md).
    """


class ConflictError(ShaheenError):
    """Raised when an action would take something already held by someone
    else — e.g. linking a Brawlhalla account another member holds (ADR-107).
    """


class InvalidCodeError(ShaheenError):
    """Raised for a one-time link code that is malformed, unknown, used or
    expired (ADR-107). Deliberately one message for all four, so the
    response never tells a guesser which part was right.
    """


class RateLimitedError(ShaheenError):
    """Raised when a caller is doing something too often (ADR-107)."""
