"""Desired Shaheen guild structure — the single source of truth.

Both the setup planner/service (what to create/verify) and the permission
checks (which role names count as "leader") read from here, so the guild
structure defined in docs/DISCORD_SPEC.md and docs/PERMISSIONS.md is only
encoded once. `logical_key` values are stable identifiers used to look up
ProvisionedResource rows — do not rename them once /setup has run against a
real guild, or the idempotency lookup will treat the resource as missing and
recreate it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import discord

from bot.palette import CREAM, EMERALD, FOREST_GREEN, GOLD, GREY

ChannelKind = Literal["text", "voice"]


@dataclass(frozen=True)
class RoleSpec:
    logical_key: str
    name: str
    color: int
    hoist: bool = True
    mentionable: bool = False
    permissions: discord.Permissions = field(default_factory=discord.Permissions.none)


@dataclass(frozen=True)
class ChannelSpec:
    logical_key: str
    name: str
    kind: ChannelKind
    topic: str | None = None


@dataclass(frozen=True)
class CategorySpec:
    logical_key: str
    name: str
    channels: tuple[ChannelSpec, ...]
    # Restricted categories are hidden from @everyone; only ROLES_WITH_STAFF_ACCESS can see them.
    restricted: bool = False


# --- Roles, highest to lowest (docs/PERMISSIONS.md) -------------------------
#
# SHAHEEN BOT is deliberately absent: it is Discord's own managed integration
# role for the bot, not one /setup creates (docs/DECISIONS.md ADR-018).

ROLE_LEADER = RoleSpec(
    logical_key="role:shaheen_leader",
    name="👑 SHAHEEN LEADER",
    color=GOLD,
    mentionable=True,
    # Server owner-equivalent by design; every other role below is deliberately
    # unprivileged so day-to-day moderation never needs Administrator.
    permissions=discord.Permissions(administrator=True),
)

ROLE_MODERATOR = RoleSpec(
    logical_key="role:moderator",
    name="🛡️ MODERATOR",
    color=EMERALD,
    mentionable=True,
    permissions=discord.Permissions(
        kick_members=True,
        moderate_members=True,
        manage_messages=True,
        manage_nicknames=True,
        mute_members=True,
        deafen_members=True,
        move_members=True,
    ),
)

ROLE_ELITE = RoleSpec(
    logical_key="role:elite_shaheen",
    name="🏆 ELITE SHAHEEN",
    color=GOLD,
)

ROLE_SHAHEEN = RoleSpec(
    logical_key="role:shaheen",
    name="🦅 SHAHEEN",
    color=FOREST_GREEN,
)

ROLE_TRIAL = RoleSpec(
    logical_key="role:trial_shaheen",
    name="🎯 TRIAL SHAHEEN",
    color=EMERALD,
)

ROLE_ALLY = RoleSpec(
    logical_key="role:ally",
    name="🤝 ALLY",
    color=CREAM,
)

ROLE_GUEST = RoleSpec(
    logical_key="role:guest",
    name="👀 GUEST",
    color=GREY,
    hoist=False,
)

# --- Self-assignable roles (opt-in pings/tags, not clan rank) ---------------
#
# Deliberately separate from the rank ladder above: these carry no
# permissions, aren't staff-assigned, and members toggle them themselves via
# the persistent panel bot/views/roles.py posts to #roles (docs/DECISIONS.md
# ADR-058). Not in ROLES_WITH_STAFF_ACCESS. hoist=False so they don't create
# extra sidebar groupings alongside the real rank roles.

ROLE_TOURNAMENT_ALERTS = RoleSpec(
    logical_key="role:tournament_alerts",
    name="🔔 Tournament Alerts",
    color=GOLD,
    hoist=False,
    mentionable=True,
)

ROLE_SCRIM_ALERTS = RoleSpec(
    logical_key="role:scrim_alerts",
    name="📣 Scrim Alerts",
    color=EMERALD,
    hoist=False,
    mentionable=True,
)

ROLE_REGION_PAKISTAN = RoleSpec(
    logical_key="role:region_pakistan",
    name="🇵🇰 Pakistan",
    color=FOREST_GREEN,
    hoist=False,
)

ROLE_REGION_INTERNATIONAL = RoleSpec(
    logical_key="role:region_international",
    name="🌍 International",
    color=CREAM,
    hoist=False,
)

ROLE_MODE_1V1 = RoleSpec(
    logical_key="role:mode_1v1",
    name="🥊 1v1 Player",
    color=GREY,
    hoist=False,
)

ROLE_MODE_2V2 = RoleSpec(
    logical_key="role:mode_2v2",
    name="👥 2v2 Player",
    color=GREY,
    hoist=False,
)

# Order here is display order on the self-assign panel, not hierarchy.
SELF_ASSIGN_ROLES: tuple[RoleSpec, ...] = (
    ROLE_TOURNAMENT_ALERTS,
    ROLE_SCRIM_ALERTS,
    ROLE_REGION_PAKISTAN,
    ROLE_REGION_INTERNATIONAL,
    ROLE_MODE_1V1,
    ROLE_MODE_2V2,
)

# Highest position first — /setup creates/repairs roles in this order and
# leaves later roles positioned below earlier ones. Self-assign roles are
# appended last (lowest position) since they carry no rank/permissions.
ROLES: tuple[RoleSpec, ...] = (
    ROLE_LEADER,
    ROLE_MODERATOR,
    ROLE_ELITE,
    ROLE_SHAHEEN,
    ROLE_TRIAL,
    ROLE_ALLY,
    ROLE_GUEST,
    *SELF_ASSIGN_ROLES,
)

# Roles authorized to see restricted categories (DEVELOPMENT, SHAHEEN ARENA
# until launch) in addition to the /setup-authorized fallback in
# bot/checks/permissions.py.
ROLES_WITH_STAFF_ACCESS: tuple[RoleSpec, ...] = (ROLE_LEADER, ROLE_MODERATOR)


# --- Categories & channels (docs/DISCORD_SPEC.md) ---------------------------

CATEGORIES: tuple[CategorySpec, ...] = (
    CategorySpec(
        logical_key="category:shaheen_hq",
        name="🏯 SHAHEEN HQ",
        channels=(
            ChannelSpec("channel:announcements", "📢-announcements", "text"),
            ChannelSpec("channel:welcome", "👋-welcome", "text"),
            ChannelSpec("channel:rules", "📜-rules", "text"),
            ChannelSpec("channel:roles", "🎭-roles", "text"),
            ChannelSpec("channel:clan_info", "🦅-clan-info", "text"),
        ),
    ),
    CategorySpec(
        logical_key="category:the_nest",
        name="🪹 THE NEST",
        channels=(
            ChannelSpec("channel:general", "💬-general", "text"),
            ChannelSpec("channel:pakistan_chat", "🇵🇰-pakistan-chat", "text"),
            ChannelSpec("channel:memes", "😂-memes", "text"),
            ChannelSpec("channel:clips", "🎬-clips", "text"),
        ),
    ),
    CategorySpec(
        logical_key="category:brawlhalla",
        name="⚔️ BRAWLHALLA",
        channels=(
            ChannelSpec("channel:brawlhalla", "🎮-brawlhalla", "text"),
            ChannelSpec("channel:tips_guides", "🧠-tips-guides", "text"),
            ChannelSpec("channel:legend_talk", "🐺-legend-talk", "text"),
            ChannelSpec("channel:one_v_one", "⚔️-1v1", "text"),
            ChannelSpec("channel:two_v_two", "👥-2v2", "text"),
            ChannelSpec("channel:ranked", "🏆-ranked", "text"),
        ),
    ),
    CategorySpec(
        logical_key="category:shaheen_arena",
        name="🏟️ SHAHEEN ARENA",
        restricted=True,  # hidden/disabled from public users until there is a need
        channels=(
            ChannelSpec("channel:scrims", "⚔️-scrims", "text"),
            ChannelSpec("channel:tournaments", "🏆-tournaments", "text"),
            ChannelSpec("channel:leaderboard", "📊-leaderboard", "text"),
            ChannelSpec("channel:hall_of_fame", "🥇-hall-of-fame", "text"),
        ),
    ),
    CategorySpec(
        logical_key="category:voice",
        name="🎙️ VOICE",
        channels=(
            ChannelSpec("channel:voice_the_nest", "🔊-the-nest", "voice"),
            ChannelSpec("channel:voice_gaming", "🎮-gaming", "voice"),
            ChannelSpec("channel:voice_ranked", "⚔️-ranked", "voice"),
            ChannelSpec("channel:voice_afk", "💤-afk", "voice"),
        ),
    ),
    CategorySpec(
        logical_key="category:development",
        name="🛠️ DEVELOPMENT",
        restricted=True,  # admin-only
        channels=(
            ChannelSpec("channel:bot_testing", "🤖-bot-testing", "text"),
            ChannelSpec("channel:website_testing", "🌐-website-testing", "text"),
            ChannelSpec("channel:commands", "🧪-commands", "text"),
            ChannelSpec("channel:bug_reports", "🐛-bug-reports", "text"),
            ChannelSpec("channel:development_log", "📝-development-log", "text"),
        ),
    ),
)
