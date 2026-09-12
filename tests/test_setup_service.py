"""SetupService permission-overwrite computation and reconciliation.

docs/DECISIONS.md ADR-069: a `gated` category is hidden from @everyone AND
Guest, visible to VERIFIED_ROLES; and overwrites are now always reconciled
(even an empty dict) instead of being skipped, which is what actually clears
a stray manual overwrite left on a channel outside the bot's management.

docs/DECISIONS.md ADR-072: every channel now also carries an explicit copy
of its parent category's restricted/gated overwrite, rather than being
created with zero overwrites of its own and relying on Discord to cascade
the category's overwrite down to it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord

from bot.constants import (
    CATEGORIES,
    ROLE_ALLY,
    ROLE_GUEST,
    ROLE_LEADER,
    ROLE_MODERATOR,
    CategorySpec,
    ChannelSpec,
)
from services.setup_planner import ActionType, CategoryAction, ChannelAction
from services.setup_service import SetupReport, SetupService

_EVERYONE = object()
_GUEST = object()
_LEADER = object()
_MODERATOR = object()
_ALLY = object()

_ROLE_BY_KEY = {
    ROLE_GUEST.logical_key: _GUEST,
    ROLE_LEADER.logical_key: _LEADER,
    ROLE_MODERATOR.logical_key: _MODERATOR,
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


# ---------- ADR-072: channels carry an explicit copy of the parent's gate ----------


def test_channel_overwrites_copies_gated_parent() -> None:
    parent = CategorySpec(logical_key="category:test", name="TEST", channels=(), gated=True)
    spec = ChannelSpec(logical_key="channel:test", name="test", kind="text")

    overwrites = _service()._channel_overwrites(spec, parent, _ROLE_BY_KEY)

    assert overwrites[_EVERYONE].view_channel is False
    assert overwrites[_GUEST].view_channel is False
    assert overwrites[_ALLY].view_channel is True


def test_channel_overwrites_copies_restricted_parent() -> None:
    parent = CategorySpec(logical_key="category:test", name="TEST", channels=(), restricted=True)
    spec = ChannelSpec(logical_key="channel:test", name="test", kind="text")

    overwrites = _service()._channel_overwrites(spec, parent, _ROLE_BY_KEY)

    assert overwrites[_EVERYONE].view_channel is False
    assert overwrites[_LEADER].view_channel is True


def test_channel_overwrites_no_parent_and_not_staff_only_send_is_empty() -> None:
    spec = ChannelSpec(logical_key="channel:test", name="test", kind="text")
    assert _service()._channel_overwrites(spec, None, _ROLE_BY_KEY) == {}


def test_channel_overwrites_staff_only_send_layers_over_gated_parent() -> None:
    """A channel that's both in a gated category AND staff_only_send
    should keep the parent's view_channel grants while adding its own
    send_messages restriction on top, not replace one with the other.
    """
    parent = CategorySpec(logical_key="category:test", name="TEST", channels=(), gated=True)
    spec = ChannelSpec(logical_key="channel:test", name="test", kind="text", staff_only_send=True)

    overwrites = _service()._channel_overwrites(spec, parent, _ROLE_BY_KEY)

    assert overwrites[_EVERYONE].view_channel is False  # from the gated parent
    assert overwrites[_EVERYONE].send_messages is False  # from staff_only_send
    assert overwrites[_ALLY].view_channel is True  # verified role still granted view
    assert overwrites[_MODERATOR].send_messages is True  # staff granted send


def test_channel_overwrites_mutating_a_copy_does_not_leak_into_category_overwrites() -> None:
    """The channel-level dict must be independent PermissionOverwrite
    instances, not the same objects _category_overwrites returns — else
    layering staff_only_send on top of a copy would corrupt the category's
    own overwrite the next time it's computed.
    """
    parent = CategorySpec(logical_key="category:test", name="TEST", channels=(), gated=True)
    spec = ChannelSpec(logical_key="channel:test", name="test", kind="text", staff_only_send=True)
    service = _service()

    service._channel_overwrites(spec, parent, _ROLE_BY_KEY)
    category_overwrites = service._category_overwrites(parent, _ROLE_BY_KEY)

    assert category_overwrites[_EVERYONE].send_messages is None  # untouched by the channel copy


async def test_apply_channels_applies_parent_gate_to_a_real_gated_channel() -> None:
    """End-to-end regression for the actual reported bug: a brand-new
    channel created inside THE NEST (gated=True in bot/constants.py) must
    get the gate's overwrite on creation, not zero overwrites relying on
    Discord to cascade it down from the category.
    """
    the_nest = next(c for c in CATEGORIES if c.logical_key == "category:the_nest")
    general_spec = next(ch for ch in the_nest.channels if ch.logical_key == "channel:general")
    assert the_nest.gated is True

    service = _service()
    service._remember = AsyncMock()  # type: ignore[method-assign]
    guild_channel = Mock(spec=discord.TextChannel)
    guild_channel.id = 42
    guild_channel.edit = AsyncMock()
    service._guild.get_channel = Mock(return_value=guild_channel)

    role_by_key = {
        ROLE_GUEST.logical_key: _GUEST,
        ROLE_ALLY.logical_key: _ALLY,
    }
    action = ChannelAction(
        type=ActionType.VERIFY,
        spec=general_spec,
        category_logical_key="category:the_nest",
        existing_id=42,
    )
    report = SetupReport(mode="launch")

    await service._apply_channels((action,), {}, role_by_key, report)

    guild_channel.edit.assert_awaited_once()
    applied = guild_channel.edit.await_args.kwargs["overwrites"]
    assert applied[_EVERYONE].view_channel is False
    assert applied[_GUEST].view_channel is False
    assert applied[_ALLY].view_channel is True
