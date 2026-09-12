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
from services.clan_service import LegendMetaEntry


def _legend_display_name(legend_name_key: str) -> str:
    # Same heuristic as bot/content/profile_embeds.py's private helper of
    # the same name — the API only gives an internal key (e.g. "bodvar"),
    # title-cased as a reasonable display name. Small intentional
    # duplication rather than a cross-module import for one string
    # formatting rule.
    return legend_name_key.replace("_", " ").title()


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


def build_tier_change_announcement_embed(
    *, display_name: str, player_name: str, old_tier: str, new_tier: str, promoted: bool
) -> discord.Embed:
    """docs/DECISIONS.md ADR-068 — a tier change is family-level only
    (Gold -> Platinum), not sub-rank (Platinum III -> Platinum II).
    """
    if promoted:
        return discord.Embed(
            title="🔼 Ranked Promotion!",
            description=f"**{display_name}** ({player_name}) climbed from **{old_tier}** to "
            f"**{new_tier}**!",
            colour=GOLD,
        )
    return discord.Embed(
        title="🔽 Ranked Demotion",
        description=f"**{display_name}** ({player_name}) dropped from **{old_tier}** to "
        f"**{new_tier}**.",
        colour=FOREST_GREEN,
    )


def build_weekly_digest_embed(
    *,
    rating_gains: list[tuple[str, int]],
    top_chatters: list[tuple[str, int]],
    matches_played: int,
) -> discord.Embed:
    """docs/DECISIONS.md ADR-070. `rating_gains`/`top_chatters` are already
    resolved (display_name, value) pairs, sorted best-first — the cog
    resolves discord_id -> display_name the same way /leaderboard does,
    since bot/content stays Discord-agnostic-data-in, embed-out.
    """
    embed = discord.Embed(title="📅 Weekly Shaheen Recap", colour=GOLD)
    if rating_gains:
        lines = [
            f"**{i}.** {name} (+{gain})"
            for i, (name, gain) in enumerate(rating_gains, start=1)
        ]
        embed.add_field(name="📈 Top Rating Gains", value="\n".join(lines), inline=False)
    if top_chatters:
        lines = [f"**{i}.** {name} ({xp} XP)" for i, (name, xp) in enumerate(top_chatters, start=1)]
        embed.add_field(name="💬 Most Active Chatters", value="\n".join(lines), inline=False)
    embed.add_field(name="⚔️ Matches Played", value=str(matches_played), inline=False)
    if not rating_gains and not top_chatters and not matches_played:
        embed.description = "A quiet week — nothing to report yet."
    return embed


def build_mvp_announcement_embed(*, display_name: str, reason: str) -> discord.Embed:
    return discord.Embed(
        title="🌟 MVP of the Week",
        description=f"**{display_name}** — {reason}. Wear the crown proudly!",
        colour=GOLD,
    )


def build_spotlight_embed(*, display_name: str, note: str, staff_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"✨ Member Spotlight — {display_name}",
        description=note,
        colour=GOLD,
    )
    embed.set_footer(text=f"Featured by {staff_name}")
    return embed


def build_legend_meta_embed(entries: list[LegendMetaEntry]) -> discord.Embed:
    """Clan-wide Legend popularity/win-rate (docs/DECISIONS.md ADR-068) —
    entries already sorted most-played-first and filtered to a minimum
    combined-games threshold by ClanService.legend_meta.
    """
    embed = discord.Embed(title="🐺 Shaheen Legend Meta", colour=EMERALD)
    if not entries:
        embed.description = "Not enough played games yet to show a meaningful Legend meta."
        return embed

    lines = [
        f"**{idx}. {_legend_display_name(e.legend_name_key)}** — {e.total_games} games "
        f"across {e.player_count} member(s), {e.win_rate:.0f}% win rate"
        for idx, e in enumerate(entries, start=1)
    ]
    embed.description = "\n".join(lines)
    return embed
