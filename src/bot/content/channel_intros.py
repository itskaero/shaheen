"""Starter "what this channel is for" embeds for /setup run mode:launch.

One function per BRAWLISTAN channel that the welcome/rules embeds don't
already cover (bot/cogs/setup.py's _launch_messages, docs/DECISIONS.md
ADR-059, ADR-109). Kept separate from bot/content/embeds.py so that file
doesn't grow one function per channel. Calm product copy (docs/BRAND.md):
short headings, restrained emoji, concise.
"""

from __future__ import annotations

import discord

from bot.palette import CREAM, EMERALD, FOREST_GREEN, GOLD, GREY

# --- START HERE ----------------------------------------------------------


def build_announcements_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="📢 Announcements",
        description="BRAWLISTAN news: new seasons, tournaments, featured players and updates.",
        colour=GOLD,
    )


# --- BRAWLISTAN ----------------------------------------------------------


def build_rankings_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🏆 Rankings",
        description=(
            "Pakistan's Brawlhalla rankings — weekly standings and the week's biggest "
            "climbers land here.\n\n"
            "Not on the board yet? Run `/link` with your Brawlhalla ID, or "
            "`/pakistan join`. The full table lives on the website."
        ),
        colour=GOLD,
    )


def build_tournaments_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🏟️ Tournaments",
        description="Upcoming tournaments, sign-ups and results. Use `/tournament register` "
        "to enter one that's open.",
        colour=GOLD,
    )


def build_looking_for_game_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🎮 Looking for Game",
        description=(
            "Find a 1v1 sparring partner or a 2v2 teammate. Say your region, rating and "
            "what you want to play — or use the buttons below."
        ),
        colour=EMERALD,
    )


# --- COMMUNITY -----------------------------------------------------------


def build_general_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="💬 General",
        description="Talk about anything — Brawlhalla, the scene, or otherwise.",
        colour=EMERALD,
    )


def build_clips_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🎬 Clips",
        description="Share your best plays, combos and highlights. Clips only — chat goes "
        "in #general.",
        colour=CREAM,
    )


def build_achievements_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🏅 Achievements",
        description="Rank-ups, milestones and achievements, posted automatically as they happen.",
        colour=FOREST_GREEN,
    )


# --- SUPPORT -------------------------------------------------------------


def build_bot_commands_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🤖 Bot Commands",
        description="Run BRAWLISTAN bot commands here to keep other channels clean. Start with "
        "`/help`, `/link` and `/profile`.",
        colour=GREY,
    )


def build_report_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🛡️ Reports",
        description=(
            "Player reports from Discord and the website, and the moderation log. "
            "Staff review each one here."
        ),
        colour=GREY,
    )
