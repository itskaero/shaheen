"""EmojiService (docs/DECISIONS.md ADR-090).

The service must never touch an emoji name that already exists (a staff
member's own custom pick shouldn't be silently overwritten by a resync),
and must stop uploading once the guild is out of static emoji slots rather
than raising or bulldozing on.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord

from services.emoji_service import EmojiService, available_emoji_files


def _guild(*, existing_names: set[str] = frozenset(), limit: int = 50) -> Mock:
    guild = Mock()
    guild.emojis = [Mock(name=n, animated=False) for n in existing_names]
    for emoji, n in zip(guild.emojis, existing_names, strict=True):
        emoji.name = n
    guild.emoji_limit = limit
    guild.create_custom_emoji = AsyncMock()
    return guild


def test_the_packaged_pack_is_not_empty() -> None:
    """A basic sanity check that the crops actually shipped with the repo."""
    assert len(available_emoji_files()) >= 10


async def test_sync_uploads_everything_on_an_empty_guild() -> None:
    guild = _guild()
    report = await EmojiService(guild).sync()

    files = available_emoji_files()
    assert len(report.created) == len(files)
    assert guild.create_custom_emoji.await_count == len(files)
    assert not report.skipped_existing
    assert not report.errors


async def test_sync_skips_a_name_that_already_exists() -> None:
    files = available_emoji_files()
    existing_name = files[0].stem
    guild = _guild(existing_names={existing_name})

    report = await EmojiService(guild).sync()

    assert existing_name in report.skipped_existing
    assert existing_name not in report.created
    created_names = {call.kwargs["name"] for call in guild.create_custom_emoji.await_args_list}
    assert existing_name not in created_names


async def test_sync_stops_once_the_guild_is_out_of_slots() -> None:
    files = available_emoji_files()
    guild = _guild(limit=0)

    report = await EmojiService(guild).sync()

    assert not report.created
    assert len(report.skipped_no_room) == len(files)
    guild.create_custom_emoji.assert_not_awaited()


async def test_sync_counts_only_static_emoji_against_the_limit() -> None:
    """Discord's slot limit is per animated/static — an animated emoji
    already on the guild shouldn't count against the static pack's room.
    """
    files = available_emoji_files()
    guild = _guild(limit=len(files))
    animated = Mock()
    animated.name = "some_animated_emoji"
    animated.animated = True
    guild.emojis = [animated]

    report = await EmojiService(guild).sync()

    assert len(report.created) == len(files)
    assert not report.skipped_no_room


async def test_forbidden_upload_is_recorded_not_raised() -> None:
    guild = _guild()
    guild.create_custom_emoji.side_effect = discord.Forbidden(Mock(status=403), "no perms")

    report = await EmojiService(guild).sync()

    assert not report.created
    assert len(report.errors) == len(available_emoji_files())
