"""Pure embed-construction tests for the /verify builders (docs/DECISIONS.md
ADR-069) — mirrors the pattern in test_clan_embeds.py/test_competition_embeds.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import discord

from bot.content.moderation_embeds import (
    build_already_verified_embed,
    build_verify_dm_embed,
    build_verify_success_embed,
)


def _member(mention: str = "<@1>") -> discord.abc.User:
    member = Mock(spec=discord.Member)
    member.mention = mention
    return member


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
