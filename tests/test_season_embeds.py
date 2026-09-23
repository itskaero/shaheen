"""Season badge + season-start embed (docs/DECISIONS.md ADR-102)."""

from __future__ import annotations

import discord

from bot.content.season_embeds import (
    attach_season_badge,
    build_season_start_embed,
    season_badge_path,
)
from services.seasons import SEASONS, pakistan_season


def test_every_season_has_a_badge_image() -> None:
    for offset in range(len(SEASONS)):
        season = pakistan_season(42 + offset)
        assert season is not None
        assert season_badge_path(season).is_file(), season.badge


def test_badge_is_attached_as_the_thumbnail_from_s42() -> None:
    embed = discord.Embed(title="Board")
    files = attach_season_badge(embed, 42)
    assert [f.filename for f in files] == ["season.png"]
    assert embed.thumbnail.url == "attachment://season.png"


def test_no_badge_before_s42() -> None:
    embed = discord.Embed(title="Board")
    assert attach_season_badge(embed, 41) == []
    assert embed.thumbnail.url is None


def test_season_start_embed() -> None:
    season = pakistan_season(42)
    assert season is not None
    embed, files = build_season_start_embed(season)
    assert embed.title == "🇵🇰 The Season of Zarb-e-Shaheen begins"
    assert "Pakistan Season 1" in (embed.description or "")
    assert "ضربِ شاہین" in (embed.description or "")
    assert "23 Dec 2026" in (embed.description or "")
    assert [f.filename for f in files] == ["season-badge.png"]
    assert embed.image.url == "attachment://season-badge.png"
