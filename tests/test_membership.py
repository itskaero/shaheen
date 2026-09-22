"""bot/membership.py — the two promotion paths (docs/DECISIONS.md ADR-092).

/verify grants general community access (Guest -> Ally); an approved
application grants clan roster membership (-> Trial Shaheen directly,
skipping Ally). Kept deliberately separate so "apply" means something
different from "verify" — before this ADR both called the same function
and produced the same rank.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord
import pytest

from bot.constants import ROLE_ALLY, ROLE_ELITE, ROLE_GUEST, ROLE_TRIAL
from bot.membership import (
    grant_clan_membership,
    grant_member_access,
    is_already_a_clan_member,
    is_already_verified,
)
from core.exceptions import ShaheenError


def _role(name: str) -> Mock:
    role = Mock(spec=discord.Role)
    role.name = name
    return role


def _member(*role_names: str, guild_roles: dict[str, Mock] | None = None) -> Mock:
    # The member must hold the *same* Mock instance the guild's own role
    # list does for "was it actually held" identity checks to work, exactly
    # like a real discord.Member's .roles overlapping the guild's roles.
    live_roles = guild_roles or {
        ROLE_GUEST.name: _role(ROLE_GUEST.name),
        ROLE_ALLY.name: _role(ROLE_ALLY.name),
        ROLE_TRIAL.name: _role(ROLE_TRIAL.name),
    }
    member = Mock(spec=discord.Member)
    member.roles = [live_roles.get(name) or _role(name) for name in role_names]
    member.guild = Mock()
    member.guild.roles = list(live_roles.values())
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    return member


# --- is_already_a_clan_member -----------------------------------------------


def test_a_bare_guest_is_not_a_clan_member() -> None:
    assert is_already_a_clan_member(_member(ROLE_GUEST.name)) is False


def test_an_ally_is_not_a_clan_member() -> None:
    """The whole point of ADR-092: an Ally (community-only) must still be
    able to apply for the roster.
    """
    assert is_already_a_clan_member(_member(ROLE_ALLY.name)) is False


def test_a_trial_shaheen_is_a_clan_member() -> None:
    assert is_already_a_clan_member(_member(ROLE_TRIAL.name)) is True


def test_an_elite_member_is_a_clan_member() -> None:
    """FULL_MEMBER_ROLES covers every rank above Ally, not just Trial."""
    assert is_already_a_clan_member(_member(ROLE_ELITE.name)) is True


# --- grant_clan_membership ---------------------------------------------------


async def test_grant_clan_membership_promotes_a_guest_to_trial() -> None:
    member = _member(ROLE_GUEST.name)

    await grant_clan_membership(member, reason="approved")

    member.add_roles.assert_awaited_once()
    assert member.add_roles.await_args.args[0].name == ROLE_TRIAL.name
    member.remove_roles.assert_awaited_once()
    assert member.remove_roles.await_args.args[0].name == ROLE_GUEST.name


async def test_grant_clan_membership_promotes_an_ally_to_trial_skipping_ally_removal_step() -> None:
    member = _member(ROLE_ALLY.name)

    await grant_clan_membership(member, reason="approved")

    member.add_roles.assert_awaited_once()
    assert member.add_roles.await_args.args[0].name == ROLE_TRIAL.name
    member.remove_roles.assert_awaited_once()
    assert member.remove_roles.await_args.args[0].name == ROLE_ALLY.name


async def test_grant_clan_membership_raises_when_trial_role_is_not_provisioned() -> None:
    member = _member(ROLE_GUEST.name, guild_roles={ROLE_GUEST.name: _role(ROLE_GUEST.name)})

    with pytest.raises(ShaheenError, match="run /setup run"):
        await grant_clan_membership(member, reason="approved")

    member.add_roles.assert_not_called()


async def test_grant_clan_membership_wraps_forbidden_as_shaheen_error() -> None:
    member = _member(ROLE_GUEST.name)
    member.add_roles.side_effect = discord.Forbidden(Mock(status=403), "no perms")

    with pytest.raises(ShaheenError, match="permission"):
        await grant_clan_membership(member, reason="approved")


# --- is_already_verified / grant_member_access (ADR-089, unaffected here) --


def test_a_bare_guest_is_not_already_verified() -> None:
    assert is_already_verified(_member(ROLE_GUEST.name)) is False


def test_an_ally_is_already_verified() -> None:
    assert is_already_verified(_member(ROLE_ALLY.name)) is True


async def test_grant_member_access_promotes_a_guest_to_ally_only() -> None:
    """/verify's promotion must never reach for Trial Shaheen — that's the
    application-approval path's job, not this one's.
    """
    member = _member(ROLE_GUEST.name)

    await grant_member_access(member, reason="verified")

    member.add_roles.assert_awaited_once()
    assert member.add_roles.await_args.args[0].name == ROLE_ALLY.name
