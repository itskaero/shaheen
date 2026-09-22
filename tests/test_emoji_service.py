"""EmojiService (docs/DECISIONS.md ADR-090).

The service must never touch an emoji name that already exists (a staff
member's own custom pick shouldn't be silently overwritten by a resync),
and must stop uploading once the guild is out of static emoji slots rather
than raising or bulldozing on.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord

from services.emoji_service import (
    EmojiService,
    available_emoji_files,
    candidate_files,
    candidate_legends,
)


def _guild(*, existing_names: set[str] = frozenset(), limit: int = 50) -> Mock:
    guild = Mock()
    guild.emojis = [Mock(name=n, animated=False) for n in existing_names]
    for emoji, n in zip(guild.emojis, existing_names, strict=True):
        emoji.name = n
        emoji.delete = AsyncMock()
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


# --- candidate pool (docs/DECISIONS.md ADR-092) -----------------------------


def test_candidate_legends_is_not_empty() -> None:
    """The candidate pool actually shipped with the repo."""
    legends = candidate_legends()
    assert len(legends) >= 10
    assert legends == tuple(sorted(legends))


def test_candidate_files_returns_crops_for_a_real_legend() -> None:
    legend = candidate_legends()[0]
    files = candidate_files(legend)
    assert len(files) > 0
    assert files == tuple(sorted(files))


def test_candidate_files_is_empty_for_an_unknown_legend() -> None:
    """A stale/renamed folder shouldn't crash the picker mid-browse."""
    assert candidate_files("not_a_real_legend") == ()


# --- sync(files=...) — the picker's explicit-upload path --------------------


async def test_sync_with_explicit_files_ignores_the_curated_pack() -> None:
    legend = candidate_legends()[0]
    path = candidate_files(legend)[0]
    guild = _guild()

    report = await EmojiService(guild).sync(files=[("my_custom_name", path)])

    assert report.created == ["my_custom_name"]
    guild.create_custom_emoji.assert_awaited_once()
    assert guild.create_custom_emoji.await_args.kwargs["name"] == "my_custom_name"


async def test_sync_with_explicit_files_still_skips_existing_names() -> None:
    legend = candidate_legends()[0]
    path = candidate_files(legend)[0]
    guild = _guild(existing_names={"taken"})

    report = await EmojiService(guild).sync(files=[("taken", path)])

    assert report.skipped_existing == ["taken"]
    guild.create_custom_emoji.assert_not_awaited()


async def test_sync_with_explicit_files_still_respects_the_slot_limit() -> None:
    legend = candidate_legends()[0]
    path = candidate_files(legend)[0]
    guild = _guild(limit=0)

    report = await EmojiService(guild).sync(files=[("anything", path)])

    assert report.skipped_no_room == ["anything"]
    guild.create_custom_emoji.assert_not_awaited()


async def test_sync_with_an_empty_explicit_list_uploads_nothing() -> None:
    guild = _guild()

    report = await EmojiService(guild).sync(files=[])

    assert report.total == 0
    guild.create_custom_emoji.assert_not_awaited()


# --- clear() — /emoji clear (docs/DECISIONS.md ADR-093) ---------------------


async def test_clear_deletes_every_emoji_regardless_of_origin() -> None:
    guild = _guild(existing_names={"random_staff_upload", "koji_gg"})

    report = await EmojiService(guild).clear()

    assert set(report.deleted) == {"random_staff_upload", "koji_gg"}
    assert not report.errors
    for emoji in guild.emojis:
        emoji.delete.assert_awaited_once_with(reason="Shaheen /emoji clear")


async def test_clear_collects_forbidden_without_aborting_the_batch() -> None:
    guild = _guild(existing_names={"a", "b"})
    forbidden_emoji = next(e for e in guild.emojis if e.name == "a")
    forbidden_emoji.delete.side_effect = discord.Forbidden(Mock(status=403), "no perms")

    report = await EmojiService(guild).clear()

    assert report.deleted == ["b"]
    assert len(report.errors) == 1
    assert "'a'" in report.errors[0]


async def test_clear_no_ops_on_an_empty_guild() -> None:
    guild = _guild()

    report = await EmojiService(guild).clear()

    assert report.total == 0
    assert report.deleted == []
    assert report.errors == []
