"""Permission checks for setup commands.

See docs/DECISIONS.md ADR-010: /setup is authorized for the guild owner, any
member with the native Administrator permission, or a holder of the
👑 SHAHEEN LEADER role. The Administrator/owner fallback is permanent, not a
one-time bootstrap step, because the Leader role does not exist until
/setup creates it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

import discord
from discord import app_commands

from bot.constants import ROLE_LEADER
from core.exceptions import PermissionDeniedError

T = TypeVar("T")


def is_setup_authorized(
    *, is_owner: bool, is_administrator: bool, role_names: Iterable[str]
) -> bool:
    """Pure decision logic — see docs/DECISIONS.md ADR-010."""
    if is_owner or is_administrator:
        return True
    return ROLE_LEADER.name in role_names


def check_setup_authorized(member: discord.Member) -> bool:
    """Discord-facing wrapper around `is_setup_authorized`."""
    return is_setup_authorized(
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
