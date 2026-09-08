"""Branded embeds for /leaderboard, /achievements, /history, and Hall of Fame
announcements (docs/DECISIONS.md ADR-032).
"""

from __future__ import annotations

from datetime import datetime

import discord

from bot.palette import EMERALD, FOREST_GREEN, GOLD
from database.models.achievement import Achievement
from database.models.ranking_snapshot import RankingSnapshot
from services.achievements import AchievementDef


def build_leaderboard_embed(
    entries: list[tuple[str, str | None, int | None]],
) -> discord.Embed:
    """entries: (display_name, tier, rating), already sorted best-first."""
    embed = discord.Embed(title="🏆 Shaheen Leaderboard", colour=GOLD)
    if not entries:
        embed.description = "No ranked snapshots yet — link a Brawlhalla account with `/link`."
        return embed

    lines = [
        f"**{idx}.** {name} — {rating if rating is not None else '—'} rating"
        + (f" ({tier})" if tier else "")
        for idx, (name, tier, rating) in enumerate(entries, start=1)
    ]
    embed.description = "\n".join(lines)
    return embed


def build_history_embed(
    *, display_name: str, player_name: str, snapshots: list[RankingSnapshot]
) -> discord.Embed:
    embed = discord.Embed(title=f"📈 {display_name} — Rating History", colour=EMERALD)
    if not snapshots:
        embed.description = f"No stored snapshots yet for **{player_name}**."
        return embed

    lines = [
        f"{snap.captured_at:%Y-%m-%d} — {snap.rating if snap.rating is not None else '—'} rating"
        + (f" ({snap.tier})" if snap.tier else "")
        for snap in snapshots
    ]
    embed.description = "\n".join(lines)
    return embed


def build_achievements_embed(
    *, display_name: str, entries: list[tuple[Achievement, datetime]]
) -> discord.Embed:
    embed = discord.Embed(title=f"🥇 {display_name} — Achievements", colour=GOLD)
    if not entries:
        embed.description = "No achievements earned yet."
        return embed

    lines = [
        f"**{achievement.name}** — {achievement.description} ({awarded_at:%Y-%m-%d})"
        for achievement, awarded_at in entries
    ]
    embed.description = "\n".join(lines)
    return embed


def build_achievement_announcement_embed(
    *, display_name: str, achievement: AchievementDef
) -> discord.Embed:
    return discord.Embed(
        title="🥇 New Achievement!",
        description=f"**{display_name}** earned **{achievement.name}** — {achievement.description}",
        colour=GOLD,
    )


def build_milestone_announcement_embed(
    *, display_name: str, player_name: str, new_peak_rating: int
) -> discord.Embed:
    return discord.Embed(
        title="📈 New Career-Peak Rating!",
        description=f"**{display_name}** ({player_name}) reached a new peak rating of "
        f"**{new_peak_rating}**.",
        colour=FOREST_GREEN,
    )
