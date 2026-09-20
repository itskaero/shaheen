"""Pure embed-construction tests for the /verify builders (docs/DECISIONS.md
ADR-069) — mirrors the pattern in test_clan_embeds.py/test_competition_embeds.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import discord

from bot.content.moderation_embeds import (
    build_already_verified_embed,
    build_lock_log_embed,
    build_mod_log_embed,
    build_nickname_log_embed,
    build_slowmode_log_embed,
    build_unban_log_embed,
    build_unlock_log_embed,
    build_untimeout_log_embed,
    build_verify_dm_embed,
    build_verify_success_embed,
)


def _member(mention: str = "<@1>") -> discord.abc.User:
    member = Mock(spec=discord.Member)
    member.mention = mention
    member.display_avatar = Mock(url="https://example.com/avatar.png")
    member.__str__ = Mock(return_value="Member#0001")  # type: ignore[method-assign]
    return member


def _channel(mention: str = "<#1>") -> discord.TextChannel:
    channel = Mock(spec=discord.TextChannel)
    channel.mention = mention
    return channel


def test_verify_success_embed_mentions_target() -> None:
    embed = build_verify_success_embed(target=_member("<@42>"))
    assert "<@42>" in embed.description


def test_already_verified_embed_mentions_target() -> None:
    embed = build_already_verified_embed(target=_member("<@42>"))
    assert "<@42>" in embed.description
    assert "already" in embed.description.lower()


def test_verify_dm_embed_includes_guild_name() -> None:
    embed = build_verify_dm_embed(guild_name="Shaheen")
    assert "Shaheen" in embed.title


def test_mod_log_embed_has_target_thumbnail_and_moderator_footer() -> None:
    target = _member("<@42>")
    moderator = _member("<@9>")

    embed = build_mod_log_embed(action="Test Action", target=target, moderator=moderator)

    assert embed.thumbnail.url == "https://example.com/avatar.png"
    assert embed.footer.text is not None and "Actioned by" in embed.footer.text
    assert embed.timestamp is not None


def test_unban_log_embed_names_the_action() -> None:
    embed = build_unban_log_embed(target=_member(), moderator=_member(), reason="appeal accepted")
    assert "Unbanned" in embed.title
    assert "appeal accepted" in (embed.description or "")


def test_untimeout_log_embed_names_the_action() -> None:
    embed = build_untimeout_log_embed(target=_member(), moderator=_member(), reason=None)
    assert "Timeout Removed" in embed.title


def test_lock_log_embed_mentions_the_channel() -> None:
    embed = build_lock_log_embed(channel=_channel("<#77>"), moderator=_member(), reason="raid")
    assert "<#77>" in (embed.description or "")
    assert "raid" in (embed.description or "")


def test_unlock_log_embed_mentions_the_channel() -> None:
    embed = build_unlock_log_embed(channel=_channel("<#77>"), moderator=_member())
    assert "<#77>" in (embed.description or "")


def test_slowmode_log_embed_reports_seconds() -> None:
    embed = build_slowmode_log_embed(channel=_channel(), moderator=_member(), seconds=30)
    assert "30" in (embed.description or "")


def test_slowmode_log_embed_reports_disabled_at_zero() -> None:
    embed = build_slowmode_log_embed(channel=_channel(), moderator=_member(), seconds=0)
    assert "disabled" in (embed.description or "").lower()


def test_nickname_log_embed_shows_before_and_after() -> None:
    embed = build_nickname_log_embed(
        target=_member(),
        moderator=_member(),
        old_nick="OldName",
        new_nick="NewName",
        reason=None,
    )
    assert "OldName" in (embed.description or "")
    assert "NewName" in (embed.description or "")
