"""Granting a newcomer access to the server.

Two distinct promotions live here, kept deliberately separate
(docs/DECISIONS.md ADR-092): `/verify` grants general **community** access
(Guest -> Ally) with no form — for people who want to hang out without
trying out for the roster. An approved `/apply` application grants
**clan roster membership** (-> Trial Shaheen directly) — the applicant
already went through real screening (Brawlhalla ID, rank, "why Shaheen"),
so there's no reason to park them at Ally first. Before ADR-092 both paths
called the same function and produced the same rank, which made "apply"
indistinguishable from "verify" even though the two ask for completely
different things.

Extracted in docs/DECISIONS.md ADR-089 so every entry path promotes people
the same way as every other path that grants the *same* thing — two code
paths doing "remove Guest, add Ally" separately would drift, and a member
let in through one door but not the other is the kind of bug nobody
notices until someone can't see a channel.
"""

from __future__ import annotations

import discord

from bot.constants import FULL_MEMBER_ROLES, ROLE_ALLY, ROLE_GUEST, ROLE_TRIAL, ROLES
from core.exceptions import ShaheenError


def is_already_verified(member: discord.Member) -> bool:
    """True if the member holds any rank role above Guest.

    docs/DECISIONS.md ADR-069 — mirrors LinkCog._maybe_promote's own
    "already ranked, leave alone" check. Used by /verify: promoting an
    already-Ally-or-above member to Ally again is a no-op, not an error.
    """
    rank_role_names = {role.name for role in ROLES if role.logical_key != ROLE_GUEST.logical_key}
    return bool({role.name for role in member.roles} & rank_role_names)


def is_already_a_clan_member(member: discord.Member) -> bool:
    """True if the member already holds Trial Shaheen or above.

    docs/DECISIONS.md ADR-092 — the gate for *applying*, not for general
    verification. An Ally (let in via `/verify`, community-only) must still
    be able to apply for the roster; only an existing roster member can't.
    """
    full_member_role_names = {role.name for role in FULL_MEMBER_ROLES}
    return bool({role.name for role in member.roles} & full_member_role_names)


async def grant_member_access(member: discord.Member, *, reason: str) -> None:
    """Swap Guest for Ally — general community access, no roster status.

    What `/verify` grants. Raises ShaheenError if the role isn't
    provisioned yet or the bot lacks permission — both are actionable by
    staff, so neither is swallowed.
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


async def grant_clan_membership(member: discord.Member, *, reason: str) -> None:
    """Swap Guest and/or Ally for Trial Shaheen — real roster membership.

    What an approved `/apply` application grants (docs/DECISIONS.md
    ADR-092), skipping Ally entirely: the applicant already went through
    the form and staff review, so there's nothing left to gate on. Removes
    whichever of Guest/Ally the member currently holds. Raises ShaheenError
    if the role isn't provisioned yet or the bot lacks permission.
    """
    guild = member.guild
    guest_role = discord.utils.get(guild.roles, name=ROLE_GUEST.name)
    ally_role = discord.utils.get(guild.roles, name=ROLE_ALLY.name)
    trial_role = discord.utils.get(guild.roles, name=ROLE_TRIAL.name)
    if trial_role is None:
        raise ShaheenError(f"The {ROLE_TRIAL.name} role doesn't exist yet — run /setup run first.")

    try:
        member_role_names = {role.name for role in member.roles}
        if guest_role is not None and guest_role.name in member_role_names:
            await member.remove_roles(guest_role, reason=reason)
        if ally_role is not None and ally_role.name in member_role_names:
            await member.remove_roles(ally_role, reason=reason)
        await member.add_roles(trial_role, reason=reason)
    except discord.Forbidden as exc:
        raise ShaheenError("Missing permission to assign roles.") from exc
