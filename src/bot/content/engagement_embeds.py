"""Branded embeds for bot/cogs/engagement.py — chat level display
(docs/DECISIONS.md ADR-065).
"""

from __future__ import annotations

import discord

from bot.palette import EMERALD, GOLD
from services.chat_gamification import rank_title_for_level, xp_for_level


def build_level_embed(*, display_name: str, xp: int, level: int) -> discord.Embed:
    next_threshold = xp_for_level(level + 1)
    remaining = max(0, next_threshold - xp)
    embed = discord.Embed(title=f"📈 {display_name} — Level {level}", colour=GOLD)
    embed.add_field(name="Rank", value=rank_title_for_level(level), inline=True)
    embed.add_field(name="XP", value=f"{xp:,}", inline=True)
    embed.add_field(name="Next Level", value=f"{remaining:,} XP to go", inline=True)
    return embed


def build_chatboard_embed(entries: list[tuple[str, int, int]]) -> discord.Embed:
    """`entries` is (display_name, level, xp) tuples, highest xp first."""
    embed = discord.Embed(title="💬 Most Active Chatters", colour=EMERALD)
    if not entries:
        embed.description = "No chat activity recorded yet."
        return embed
    lines = [
        f"**{i}.** {name} — Level {level} ({xp:,} XP)"
        for i, (name, level, xp) in enumerate(entries, start=1)
    ]
    embed.description = "\n".join(lines)
    return embed


def build_level_up_embed(*, mention: str, level: int) -> discord.Embed:
    return discord.Embed(
        title="📈 Level Up!",
        description=f"{mention} reached **Level {level}** — *{rank_title_for_level(level)}*!",
        colour=GOLD,
    )
