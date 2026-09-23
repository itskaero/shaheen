"""Pakistan Season visuals for Discord (docs/DECISIONS.md ADR-102).

The badges are cut from the owner's 13-badge sheet into
src/assets/img/seasons/<badge>.png. Inside src/, so the Dockerfile's
`COPY src/` ships them the same way it ships the other bot art (ADR-060).
"""

from __future__ import annotations

from pathlib import Path

import discord

from bot.palette import GOLD
from services.seasons import PakistanSeason, pakistan_season

_SEASON_DIR = Path(__file__).resolve().parents[2] / "assets" / "img" / "seasons"
_THUMBNAIL_NAME = "season.png"


def season_badge_path(season: PakistanSeason) -> Path:
    return _SEASON_DIR / f"{season.badge}.png"


def attach_season_badge(embed: discord.Embed, brawlhalla_season: int | None) -> list[discord.File]:
    """Put the season's badge in the embed's corner.

    Returns the attachment to send alongside the embed: empty before S42 or
    if the image is missing, so a caller can always pass `files=`.
    """
    season = pakistan_season(brawlhalla_season)
    if season is None or not season_badge_path(season).is_file():
        return []
    embed.set_thumbnail(url=f"attachment://{_THUMBNAIL_NAME}")
    return [discord.File(season_badge_path(season), filename=_THUMBNAIL_NAME)]


def build_season_start_embed(season: PakistanSeason) -> tuple[discord.Embed, list[discord.File]]:
    """The #announcements post when a new Pakistan season begins."""
    embed = discord.Embed(
        title=f"🇵🇰 The Season of {season.name} begins",
        description=(
            f"# {season.name_urdu}\n"
            f"**Pakistan Season {season.number}** · Brawlhalla Season {season.brawlhalla_season}\n"
            f"Runs to about {season.ends_at:%d %b %Y}.\n\n"
            "Ranked ratings have reset. Play your placement matches, then `/refresh` "
            "to get back on the Shaheen and Pakistan boards."
        ),
        colour=GOLD,
    )
    embed.set_footer(text="Shaheen Clan · a new season every 13 weeks")
    path = season_badge_path(season)
    if not path.is_file():
        return embed, []
    embed.set_image(url="attachment://season-badge.png")
    return embed, [discord.File(path, filename="season-badge.png")]
