"""SetupService permission-overwrite computation and reconciliation.

docs/DECISIONS.md ADR-069: a `gated` category is hidden from @everyone AND
Guest, visible to VERIFIED_ROLES; and overwrites are now always reconciled
(even an empty dict) instead of being skipped, which is what actually clears
a stray manual overwrite left on a channel outside the bot's management.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord

from bot.constants import ROLE_ALLY, ROLE_GUEST, ROLE_LEADER, CategorySpec, ChannelSpec
from services.setup_planner import ActionType, CategoryAction, ChannelAction
from services.setup_service import SetupReport, SetupService

_EVERYONE = object()
_GUEST = object()
_LEADER = object()
_ALLY = object()

_ROLE_BY_KEY = {
    ROLE_GUEST.logical_key: _GUEST,
    ROLE_LEADER.logical_key: _LEADER,
    ROLE_ALLY.logical_key: _ALLY,
}


def _service() -> SetupService:
    guild = Mock()
    guild.default_role = _EVERYONE
    return SetupService(guild, session=None)  # type: ignore[arg-type]


def test_ungated_unrestricted_category_has_no_overwrites() -> None:
    spec = CategorySpec(logical_key="category:test", name="TEST", channels=())
    assert _service()._category_overwrites(spec, _ROLE_BY_KEY) == {}


def test_restricted_category_hides_from_everyone_grants_staff() -> None:
    spec = CategorySpec(logical_key="category:test", name="TEST", channels=(), restricted=True)
    overwrites = _service()._category_overwrites(spec, _ROLE_BY_KEY)
    assert overwrites[_EVERYONE].view_channel is False
    assert overwrites[_LEADER].view_channel is True
    assert _GUEST not in overwrites  # unaffected — restricted is a staff concept, not a gate


def test_gated_category_hides_from_everyone_and_guest_grants_verified_roles() -> None:
    spec = CategorySpec(logical_key="category:test", name="TEST", channels=(), gated=True)
    overwrites = _service()._category_overwrites(spec, _ROLE_BY_KEY)
    assert overwrites[_EVERYONE].view_channel is False
    assert overwrites[_GUEST].view_channel is False
    assert overwrites[_LEADER].view_channel is True
    assert overwrites[_ALLY].view_channel is True


async def test_apply_categories_edits_overwrites_even_when_empty() -> None:
    """Regression: the `if overwrites:` guard used to skip .edit() entirely
    for non-special categories, so a stray manual overwrite (e.g. one added
    directly in Discord's UI) could never be cleared by /setup run.
    """
    service = _service()
    service._remember = AsyncMock()  # type: ignore[method-assign]

    category = Mock(spec=discord.CategoryChannel)
    category.id = 1
    category.edit = AsyncMock()
    service._guild.get_channel = Mock(return_value=category)

    spec = CategorySpec(logical_key="category:test", name="TEST", channels=())
    action = CategoryAction(type=ActionType.VERIFY, spec=spec, existing_id=1)
    report = SetupReport(mode="launch")

    await service._apply_categories((action,), {}, report)

    category.edit.assert_awaited_once_with(overwrites={}, reason="Shaheen /setup")


async def test_apply_channels_edits_overwrites_even_when_empty() -> None:
    service = _service()
    service._remember = AsyncMock()  # type: ignore[method-assign]

    channel = Mock(spec=discord.TextChannel)
    channel.id = 2
    channel.edit = AsyncMock()
    service._guild.get_channel = Mock(return_value=channel)

    spec = ChannelSpec(logical_key="channel:test", name="test", kind="text")
    action = ChannelAction(
        type=ActionType.VERIFY, spec=spec, category_logical_key="category:test", existing_id=2
    )
    report = SetupReport(mode="launch")

    await service._apply_channels((action,), {}, {}, report)

    channel.edit.assert_awaited_once_with(overwrites={}, reason="Shaheen /setup")
