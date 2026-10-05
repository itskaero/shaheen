"""Permission checks.

See docs/DECISIONS.md:
- ADR-010: `/setup` is authorized for the guild owner, any member with the
  native Administrator permission, or a holder of a leadership role
  (Founder or Admin since ADR-109). The Administrator/owner fallback is
  permanent, not a one-time bootstrap step, because the roles do not exist
  until /setup creates them.
- ADR-036: staff actions short of full server administration (moderation,
  tournaments, verification) are authorized for the same owner/admin
  fallback, or a holder of any staff role (Founder, Admin, Moderator).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

import discord
from discord import app_commands

from bot.constants import LEADERSHIP_ROLES, STAFF_ROLES, RoleSpec
from core.exceptions import PermissionDeniedError

T = TypeVar("T")


def _names(roles: Iterable[RoleSpec]) -> str:
    names = [role.name for role in roles]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} or {names[-1]}"


def _role_authorized(
    *, is_owner: bool, is_administrator: bool, role_names: Iterable[str], allowed_roles: set[str]
) -> bool:
    if is_owner or is_administrator:
        return True
    return not allowed_roles.isdisjoint(role_names)


def is_setup_authorized(
    *, is_owner: bool, is_administrator: bool, role_names: Iterable[str]
) -> bool:
    """Pure decision logic — see docs/DECISIONS.md ADR-010."""
    return _role_authorized(
        is_owner=is_owner,
        is_administrator=is_administrator,
        role_names=role_names,
        allowed_roles={role.name for role in LEADERSHIP_ROLES},
    )


def is_staff_authorized(
    *, is_owner: bool, is_administrator: bool, role_names: Iterable[str]
) -> bool:
    """Pure decision logic — see docs/DECISIONS.md ADR-036."""
    return _role_authorized(
        is_owner=is_owner,
        is_administrator=is_administrator,
        role_names=role_names,
        allowed_roles={role.name for role in STAFF_ROLES},
    )


def _is_owner(member: discord.Member, bot_owner_id: int | None) -> bool:
    # The guild owner, or BOT_OWNER_ID (core/config.py, ADR-109).
    return member.id in {member.guild.owner_id, bot_owner_id}


def _bot_owner_id(interaction: discord.Interaction) -> int | None:
    settings = getattr(interaction.client, "settings", None)
    return getattr(settings, "bot_owner_id", None)


def check_setup_authorized(member: discord.Member, bot_owner_id: int | None = None) -> bool:
    """Discord-facing wrapper around `is_setup_authorized`."""
    return is_setup_authorized(
        is_owner=_is_owner(member, bot_owner_id),
        is_administrator=member.guild_permissions.administrator,
        role_names=(role.name for role in member.roles),
    )


def check_staff_authorized(member: discord.Member, bot_owner_id: int | None = None) -> bool:
    """Discord-facing wrapper around `is_staff_authorized`."""
    return is_staff_authorized(
        is_owner=_is_owner(member, bot_owner_id),
        is_administrator=member.guild_permissions.administrator,
        role_names=(role.name for role in member.roles),
    )


def require_setup_authorized() -> Callable[[T], T]:
    """Slash-command check decorator raising a user-safe error on failure."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise PermissionDeniedError(
                "This command can only be used inside the BRAWLISTAN server."
            )
        if not check_setup_authorized(member, _bot_owner_id(interaction)):
            raise PermissionDeniedError(
                "You need to be a server administrator or hold the "
                f"{_names(LEADERSHIP_ROLES)} role to run this command."
            )
        return True

    return app_commands.check(predicate)


def require_staff_authorized() -> Callable[[T], T]:
    """Slash-command check decorator raising a user-safe error on failure."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise PermissionDeniedError(
                "This command can only be used inside the BRAWLISTAN server."
            )
        if not check_staff_authorized(member, _bot_owner_id(interaction)):
            raise PermissionDeniedError(
                "You need to be a server administrator or hold the "
                f"{_names(STAFF_ROLES)} role to run this command."
            )
        return True

    return app_commands.check(predicate)
