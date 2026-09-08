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
