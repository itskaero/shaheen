"""Desired BRAWLISTAN Discord structure — the single source of truth
(docs/DECISIONS.md ADR-109, docs/BRAWLISTAN_MIGRATION.md).

The server stays small: seven roles and twelve text channels in four
categories. /setup creates or reuses them and never sets permissions:
roles are created with none, channels get no permission overwrites, and
existing roles are never re-permissioned (repair only renames). The owner
configures who sees and does what, by hand.

`logical_key` values are stable identifiers for ProvisionedResource rows.
Where a SHAHEEN-era resource plays the same part, its key is reused, so the
existing role/channel (and its members/history) carries over instead of
being deleted and recreated:
- Founder reuses the Leader role ("role:shaheen_leader");
- #rankings reuses #leaderboard, #looking-for-game reuses #ranked,
  #achievements reuses #hall-of-fame, #bot-commands reuses #commands.
Do not rename keys once /setup has run against a real guild.
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
    # Always none for BRAWLISTAN roles (brief: never grant dangerous
    # permissions); kept as a field so the type stays explicit.
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


# --- Roles, highest to lowest ------------------------------------------------
# The bot's own managed integration role is Discord's, not /setup's.

ROLE_FOUNDER = RoleSpec(logical_key="role:shaheen_leader", name="Founder", color=GOLD)
ROLE_ADMIN = RoleSpec(logical_key="role:admin", name="Admin", color=EMERALD)
ROLE_MODERATOR = RoleSpec(
    logical_key="role:moderator", name="Moderator", color=EMERALD, mentionable=True
)
ROLE_TEAM_CAPTAIN = RoleSpec(logical_key="role:team_captain", name="Team Captain", color=CREAM)
ROLE_CONTRIBUTOR = RoleSpec(
    logical_key="role:contributor", name="Contributor", color=CREAM, hoist=False
)
# Staff confirmed the member owns their linked Brawlhalla account (/verify, ADR-107).
ROLE_VERIFIED = RoleSpec(
    logical_key="role:verified", name="Verified", color=FOREST_GREEN, hoist=False
)
# Has a linked Brawlhalla account (/link or a website claim).
ROLE_PLAYER = RoleSpec(logical_key="role:player", name="Player", color=GREY, hoist=False)

ROLES: tuple[RoleSpec, ...] = (
    ROLE_FOUNDER,
    ROLE_ADMIN,
    ROLE_MODERATOR,
    ROLE_TEAM_CAPTAIN,
    ROLE_CONTRIBUTOR,
    ROLE_VERIFIED,
    ROLE_PLAYER,
)

# Holders of these may run staff commands (bot/checks/permissions.py), on
# top of Discord's own Administrator / Manage Server permissions.
STAFF_ROLES: tuple[RoleSpec, ...] = (ROLE_FOUNDER, ROLE_ADMIN, ROLE_MODERATOR)
LEADERSHIP_ROLES: tuple[RoleSpec, ...] = (ROLE_FOUNDER, ROLE_ADMIN)

# --- Channels ----------------------------------------------------------------

CHANNEL_WELCOME = ChannelSpec(
    "channel:welcome",
    "welcome",
    "text",
    topic="Welcome to BRAWLISTAN — Pakistan's Brawlhalla Network.",
)
CHANNEL_RULES = ChannelSpec("channel:rules", "rules", "text", topic="Server rules.")
CHANNEL_ANNOUNCEMENTS = ChannelSpec(
    "channel:announcements", "announcements", "text", topic="BRAWLISTAN news, seasons and events."
)
CHANNEL_RANKINGS = ChannelSpec(
    "channel:leaderboard", "rankings", "text", topic="Pakistan rankings, climbers and rank changes."
)
CHANNEL_TOURNAMENTS = ChannelSpec(
    "channel:tournaments", "tournaments", "text", topic="Tournaments, sign-ups and results."
)
CHANNEL_LOOKING_FOR_GAME = ChannelSpec(
    "channel:ranked",
    "looking-for-game",
    "text",
    topic="Find 1v1 sparring and 2v2 partners. Try /looking.",
)
CHANNEL_GENERAL = ChannelSpec("channel:general", "general", "text", topic="General chat.")
CHANNEL_CLIPS = ChannelSpec("channel:clips", "clips", "text", topic="Share your clips.")
CHANNEL_ACHIEVEMENTS = ChannelSpec(
    "channel:hall_of_fame", "achievements", "text", topic="Milestones and achievements."
)
CHANNEL_BOT_COMMANDS = ChannelSpec(
    "channel:commands", "bot-commands", "text", topic="Use BRAWLISTAN bot commands here."
)
# Where /report and the website's Report Player land, and where moderation
# actions are logged unless MOD_LOG_CHANNEL_ID points elsewhere. The owner
# makes it staff-only.
CHANNEL_REPORT = ChannelSpec(
    "channel:report", "report", "text", topic="Player reports and moderation log (staff)."
)

CATEGORIES: tuple[CategorySpec, ...] = (
    CategorySpec(
        logical_key="category:start_here",
        name="START HERE",
        channels=(CHANNEL_WELCOME, CHANNEL_RULES, CHANNEL_ANNOUNCEMENTS),
    ),
    CategorySpec(
        logical_key="category:brawlistan",
        name="BRAWLISTAN",
        channels=(CHANNEL_RANKINGS, CHANNEL_TOURNAMENTS, CHANNEL_LOOKING_FOR_GAME),
    ),
    CategorySpec(
        logical_key="category:community",
        name="COMMUNITY",
        channels=(CHANNEL_GENERAL, CHANNEL_CLIPS, CHANNEL_ACHIEVEMENTS),
    ),
    CategorySpec(
        logical_key="category:support",
        name="SUPPORT",
        channels=(CHANNEL_BOT_COMMANDS, CHANNEL_REPORT),
    ),
)


def spec_keys() -> set[str]:
    """Every logical key the current spec owns — what /setup restructure keeps."""
    keys = {role.logical_key for role in ROLES}
    for category in CATEGORIES:
        keys.add(category.logical_key)
        keys.update(channel.logical_key for channel in category.channels)
    return keys
