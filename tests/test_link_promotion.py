"""LinkCog._maybe_promote (docs/DECISIONS.md ADR-090, superseding ADR-026).

/link used to promote a bare Guest straight to Trial Shaheen, which let
anyone skip the application/approval flow (ADR-089) entirely — link your
account before ever applying and you're in. Promotion out of Ally now
requires having actually been approved first.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord

from bot.cogs.link import LinkCog
from bot.constants import ROLE_ALLY, ROLE_ELITE, ROLE_GUEST, ROLE_TRIAL


def _role(name: str) -> Mock:
    role = Mock(spec=discord.Role)
    role.name = name
    return role


def _member(*role_names: str) -> Mock:
    # Ally/Trial are the two discord.utils.get(guild.roles, name=...) looks
    # up by name — the member must hold the *same* Mock instance for the
    # "was it actually held" identity check to see it, exactly like a real
    # discord.Member's .roles overlapping the guild's live role objects.
    guild_roles = {
        ROLE_GUEST.name: _role(ROLE_GUEST.name),
        ROLE_ALLY.name: _role(ROLE_ALLY.name),
        ROLE_TRIAL.name: _role(ROLE_TRIAL.name),
    }
    member = Mock(spec=discord.Member)
    member.roles = [guild_roles.get(name) or _role(name) for name in role_names]
    member.guild = Mock()
    member.guild.roles = list(guild_roles.values())
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    return member


def _cog() -> LinkCog:
    return LinkCog(bot=Mock())


async def test_a_bare_guest_is_not_promoted() -> None:
    """The whole point of ADR-089: linking alone must not skip approval."""
    member = _member(ROLE_GUEST.name)

    promoted = await _cog()._maybe_promote(member)

    assert promoted is False
    member.add_roles.assert_not_called()


async def test_an_approved_ally_is_promoted_to_trial() -> None:
    member = _member(ROLE_ALLY.name)

    promoted = await _cog()._maybe_promote(member)

    assert promoted is True
    member.add_roles.assert_awaited_once()
    added_role = member.add_roles.await_args.args[0]
    assert added_role.name == ROLE_TRIAL.name
    member.remove_roles.assert_awaited_once()
    removed_role = member.remove_roles.await_args.args[0]
    assert removed_role.name == ROLE_ALLY.name


async def test_a_member_already_at_trial_or_above_is_left_alone() -> None:
    member = _member(ROLE_TRIAL.name)

    promoted = await _cog()._maybe_promote(member)

    assert promoted is False
    member.add_roles.assert_not_called()


async def test_an_elite_member_is_left_alone_even_though_not_directly_checked() -> None:
    """FULL_MEMBER_ROLES covers every rank above Ally, not just Trial."""
    member = _member(ROLE_ELITE.name)

    promoted = await _cog()._maybe_promote(member)

    assert promoted is False
