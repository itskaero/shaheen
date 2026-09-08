"""Permission checks.

See docs/DECISIONS.md:
- ADR-010: `/setup` is authorized for the guild owner, any member with the
  native Administrator permission, or a holder of the 👑 SHAHEEN LEADER
  role. The Administrator/owner fallback is permanent, not a one-time
  bootstrap step, because the Leader role does not exist until /setup
  creates it.
- ADR-036: staff actions short of full server administration (tournament
  management, match dispute resolution) are authorized for the same
  owner/admin fallback, or a holder of 🛡️ MODERATOR or 👑 SHAHEEN LEADER.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

import discord
from discord import app_commands

from bot.constants import ROLE_LEADER, ROLE_MODERATOR
from core.exceptions import PermissionDeniedError

T = TypeVar("T")


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
        allowed_roles={ROLE_LEADER.name},
    )


def is_staff_authorized(
    *, is_owner: bool, is_administrator: bool, role_names: Iterable[str]
) -> bool:
    """Pure decision logic — see docs/DECISIONS.md ADR-036."""
    return _role_authorized(
        is_owner=is_owner,
        is_administrator=is_administrator,
        role_names=role_names,
        allowed_roles={ROLE_LEADER.name, ROLE_MODERATOR.name},
    )


def check_setup_authorized(member: discord.Member) -> bool:
    """Discord-facing wrapper around `is_setup_authorized`."""
    return is_setup_authorized(
        is_owner=member.guild.owner_id == member.id,
        is_administrator=member.guild_permissions.administrator,
        role_names=(role.name for role in member.roles),
    )


def check_staff_authorized(member: discord.Member) -> bool:
    """Discord-facing wrapper around `is_staff_authorized`."""
    return is_staff_authorized(
        is_owner=member.guild.owner_id == member.id,
        is_administrator=member.guild_permissions.administrator,
        role_names=(role.name for role in member.roles),
    )


def require_setup_authorized() -> Callable[[T], T]:
    """Slash-command check decorator raising a user-safe error on failure."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise PermissionDeniedError("This command can only be used inside the Shaheen server.")
        if not check_setup_authorized(member):
            raise PermissionDeniedError(
                "You need to be a server administrator or hold the "
                f"{ROLE_LEADER.name} role to run this command."
            )
        return True

    return app_commands.check(predicate)


def require_staff_authorized() -> Callable[[T], T]:
    """Slash-command check decorator raising a user-safe error on failure."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise PermissionDeniedError("This command can only be used inside the Shaheen server.")
        if not check_staff_authorized(member):
            raise PermissionDeniedError(
                "You need to be a server administrator or hold the "
                f"{ROLE_MODERATOR.name} or {ROLE_LEADER.name} role to run this command."
            )
        return True

    return app_commands.check(predicate)
