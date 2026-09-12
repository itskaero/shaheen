"""Starter "what this channel is for" embeds for /setup run mode:launch.

One function per channel that welcome/rules/roles doesn't already cover
(bot/cogs/setup.py's messages_by_channel_key, docs/DECISIONS.md ADR-059).
Kept separate from bot/content/embeds.py so that file doesn't balloon to
one function per channel in the server. Short, on-brand copy per
docs/BRAND.md: short headings, restrained emoji, green/gold, concise.
"""

from __future__ import annotations

import discord

from bot.palette import CREAM, EMERALD, FOREST_GREEN, GOLD, GREY

# --- SHAHEEN HQ --------------------------------------------------------


def build_announcements_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="📢 Announcements",
        description="Clan news, updates, and anything staff needs every member to see.",
        colour=GOLD,
    )


def build_clan_info_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🦅 Clan Info",
        description=(
            "Who Shaheen is and how the clan works. Use `/link` to connect your Brawlhalla "
            "account, then `/profile` any time to check your card."
        ),
        colour=FOREST_GREEN,
    )


def build_suggestions_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="💡 Suggestions",
        description="Got an idea for the clan? Run `/suggest` anywhere — it posts here "
        "anonymously, and everyone can vote with 👍/👎.",
        colour=GOLD,
    )


# --- THE NEST ------------------------------------------------------------


def build_general_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="💬 General",
        description="Talk about anything — clan life, Brawlhalla, or otherwise.",
        colour=EMERALD,
    )


def build_pakistan_chat_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🇵🇰 Pakistan Chat",
        description="For Shaheen's Pakistan-based members — chat in Urdu or English.",
        colour=FOREST_GREEN,
    )


def build_memes_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="😂 Memes",
        description="Brawlhalla memes, clan memes, whatever's funny.",
        colour=CREAM,
    )


def build_clips_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🎬 Clips", description="Share your best (or worst) Brawlhalla clips.", colour=EMERALD
    )


# --- BRAWLHALLA ------------------------------------------------------------


def build_brawlhalla_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🎮 Brawlhalla",
        description="General Brawlhalla discussion — patches, balance, the game itself.",
        colour=GOLD,
    )


def build_tips_guides_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🧠 Tips & Guides",
        description="Share and find tech, matchup notes, and guides for climbing.",
        colour=EMERALD,
    )


def build_legend_talk_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🐺 Legend Talk",
        description="Legend picks, matchups, and builds — check `/legends` for your own stats.",
        colour=FOREST_GREEN,
    )


def build_one_v_one_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="⚔️ 1v1",
        description="Coordinate 1v1s here, or use `/challenge` / `/scrim` to make it official.",
        colour=GOLD,
    )


def build_two_v_two_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="👥 2v2",
        description="Find a partner and coordinate 2v2s — `/scrim kind:2v2` announces one.",
        colour=GOLD,
    )


# --- SHAHEEN ARENA (restricted) ---------------------------------------------


def build_scrims_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="⚔️ Scrims",
        description=(
            "Scrim announcements land here automatically from `/scrim` and the 🥊 spar kiosk "
            "in #ranked — click Join to sign up."
        ),
        colour=GOLD,
    )


def build_tournaments_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🏆 Tournaments",
        description="Tournament brackets and announcements — see `/tournament` to run one.",
        colour=GOLD,
    )


def build_leaderboard_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="📊 Leaderboard",
        description="Check `/leaderboard` any time for Shaheen's current standings.",
        colour=GOLD,
    )


def build_hall_of_fame_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🥇 Hall of Fame",
        description="Milestones and achievements get announced here as members earn them.",
        colour=GOLD,
    )


# --- DEVELOPMENT (restricted, admin-only) -----------------------------------


def build_bot_testing_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🤖 Bot Testing",
        description="Test Shaheen's commands here before using them live.",
        colour=GREY,
    )


def build_website_testing_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🌐 Website Testing",
        description="Check the Shaheen website's behavior here.",
        colour=GREY,
    )


def build_commands_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🧪 Commands",
        description="A scratch channel for trying out slash commands.",
        colour=GREY,
    )


def build_bug_reports_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🐛 Bug Reports",
        description="Report anything broken in the bot or website here.",
        colour=GREY,
    )


def build_development_log_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="📝 Development Log",
        description="Notable changes and deploys, for staff reference.",
        colour=GREY,
    )


# --- MODERATION ----------------------------------------------------------


def build_mod_log_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🛡️ Mod Log",
        description=(
            "Every `/warn`, `/kick`, `/ban`, `/timeout`, `/purge`, and `/clearwarnings` "
            "is logged here automatically — staff reference, not a discussion channel."
        ),
        colour=GREY,
    )
