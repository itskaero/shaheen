"""Granting a newcomer access to the member channels.

Extracted in docs/DECISIONS.md ADR-089 so /verify (bot/cogs/moderation.py)
and an approved application (bot/views/application.py) promote people the
exact same way. Two code paths doing "remove Guest, add Ally" separately
would drift, and a member let in through one door but not the other is the
kind of bug nobody notices until someone can't see a channel.
"""

from __future__ import annotations

import discord

from bot.constants import ROLE_ALLY, ROLE_GUEST, ROLES
from core.exceptions import ShaheenError


def is_already_verified(member: discord.Member) -> bool:
    """True if the member holds any rank role above Guest.

    docs/DECISIONS.md ADR-069 — mirrors LinkCog._maybe_promote's own
    "already ranked, leave alone" check.
    """
    rank_role_names = {role.name for role in ROLES if role.logical_key != ROLE_GUEST.logical_key}
    return bool({role.name for role in member.roles} & rank_role_names)


async def grant_member_access(member: discord.Member, *, reason: str) -> None:
    """Swap Guest for Ally, the one promotion every entry path performs.

    Raises ShaheenError if the roles aren't provisioned yet or the bot lacks
    permission — both are actionable by staff, so neither is swallowed.
    """
    guild = member.guild
    guest_role = discord.utils.get(guild.roles, name=ROLE_GUEST.name)
    ally_role = discord.utils.get(guild.roles, name=ROLE_ALLY.name)
    if ally_role is None:
        raise ShaheenError(f"The {ROLE_ALLY.name} role doesn't exist yet — run /setup run first.")

    try:
        if guest_role is not None and guest_role in member.roles:
            await member.remove_roles(guest_role, reason=reason)
        await member.add_roles(ally_role, reason=reason)
    except discord.Forbidden as exc:
        raise ShaheenError("Missing permission to assign roles.") from exc
