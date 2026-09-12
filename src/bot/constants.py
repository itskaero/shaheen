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
    # Everyone can still view/read; only ROLES_WITH_STAFF_ACCESS can send.
    # False (default) leaves Send Messages inherited from the category —
    # docs/DECISIONS.md ADR-060, docs/PERMISSIONS.md.
    staff_only_send: bool = False


@dataclass(frozen=True)
class CategorySpec:
    logical_key: str
    name: str
    channels: tuple[ChannelSpec, ...]
    # Restricted categories are hidden from @everyone; only ROLES_WITH_STAFF_ACCESS can see them.
    restricted: bool = False
    # Gated categories are hidden from @everyone AND Guest; visible to every
    # other rank role (VERIFIED_ROLES) once a member is manually verified —
    # docs/DECISIONS.md ADR-069, docs/PERMISSIONS.md. Mutually exclusive with
    # `restricted`: a category is either staff-only or verified-only, never both.
    gated: bool = False


# --- Roles, highest to lowest (docs/PERMISSIONS.md) -------------------------
#
# SHAHEEN BOT is deliberately absent: it is Discord's own managed integration
# role for the bot, not one /setup creates (docs/DECISIONS.md ADR-018).
#
# Bilingual "English | Urdu" names, no emoji prefix — matches the owner's own
# hand-made roles (docs/DECISIONS.md ADR-060), replacing the earlier
# "emoji + ALL CAPS" style. All rank roles now carry an owner-confirmed Urdu
# translation (docs/DECISIONS.md ADR-061).

ROLE_LEADER = RoleSpec(
    logical_key="role:shaheen_leader",
    name="Leader | سربراہ",
    color=GOLD,
    mentionable=True,
    # Server owner-equivalent by design; every other role below is deliberately
    # unprivileged so day-to-day moderation never needs Administrator.
    permissions=discord.Permissions(administrator=True),
)

ROLE_MODERATOR = RoleSpec(
    logical_key="role:moderator",
    name="Moderator | ناظم",
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
    name="Elite Shaheen | شاہینِ خاص",
    color=GOLD,
)

ROLE_SHAHEEN = RoleSpec(
    logical_key="role:shaheen",
    name="Shaheen | شاہین",
    color=FOREST_GREEN,
)

ROLE_TRIAL = RoleSpec(
    logical_key="role:trial_shaheen",
    name="Trial Shaheen | آزمائشی شاہین",
    color=EMERALD,
)

ROLE_ALLY = RoleSpec(
    logical_key="role:ally",
    name="Ally | اتحادی",
    color=CREAM,
)

ROLE_GUEST = RoleSpec(
    logical_key="role:guest",
    name="Guest | مہمان",
    color=GREY,
    hoist=False,
)

# Purely cosmetic, system-rotated weekly by ClanCog's digest loop — never
# self-assigned, not part of the rank ladder or VERIFIED_ROLES (docs/
# DECISIONS.md ADR-070). Held by at most one member at a time.
ROLE_MVP = RoleSpec(
    logical_key="role:mvp_of_the_week",
    name="🌟 MVP of the Week",
    color=GOLD,
    hoist=True,
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
    ROLE_MVP,
    *SELF_ASSIGN_ROLES,
)

# Roles authorized to see restricted categories (DEVELOPMENT, SHAHEEN ARENA
# until launch) in addition to the /setup-authorized fallback in
# bot/checks/permissions.py.
ROLES_WITH_STAFF_ACCESS: tuple[RoleSpec, ...] = (ROLE_LEADER, ROLE_MODERATOR)

# Roles authorized to see gated categories — every rank role except Guest,
# i.e. everyone who has been manually verified (docs/DECISIONS.md ADR-069).
# Guest is deliberately excluded even though it's a rank role: it's the
# auto-assigned, not-yet-verified state a new member starts in.
VERIFIED_ROLES: tuple[RoleSpec, ...] = (
    ROLE_LEADER,
    ROLE_MODERATOR,
    ROLE_ELITE,
    ROLE_SHAHEEN,
    ROLE_TRIAL,
    ROLE_ALLY,
)


# --- Categories & channels (docs/DISCORD_SPEC.md) ---------------------------

CATEGORIES: tuple[CategorySpec, ...] = (
    CategorySpec(
        logical_key="category:shaheen_hq",
        name="🏯 SHAHEEN HQ",
        channels=(
            ChannelSpec(
                "channel:announcements",
                "📢-announcements",
                "text",
                topic="Clan news and updates — staff only to post, everyone can read. | "
                "کلان کی خبریں اور اپڈیٹس — صرف اسٹاف پوسٹ کر سکتا ہے، سب پڑھ سکتے ہیں۔",
                staff_only_send=True,
            ),
            ChannelSpec(
                "channel:welcome",
                "👋-welcome",
                "text",
                topic="Start here. | یہاں سے شروع کریں۔",
            ),
            ChannelSpec(
                "channel:rules",
                "📜-rules",
                "text",
                topic="Server rules. | سرور کے قوانین۔",
            ),
            ChannelSpec(
                "channel:roles",
                "🎭-roles",
                "text",
                topic="Ranks and opt-in roles. | درجے اور اختیاری رولز۔",
            ),
            ChannelSpec(
                "channel:clan_info",
                "🦅-clan-info",
                "text",
                topic="About Shaheen. | شاہین کے بارے میں۔",
            ),
            ChannelSpec(
                "channel:suggestions",
                "💡-suggestions",
                "text",
                topic="Suggest anything for the clan — posted anonymously via /suggest. | "
                "کلان کے لیے کوئی بھی تجویز — /suggest کے ذریعے گمنام طور پر پوسٹ کریں۔",
            ),
        ),
    ),
    CategorySpec(
        logical_key="category:the_nest",
        name="🪹 THE NEST",
        gated=True,  # hidden until manually verified — docs/DECISIONS.md ADR-069
        channels=(
            ChannelSpec(
                "channel:general",
                "💬-general",
                "text",
                topic="General chat. | عمومی گفتگو۔",
            ),
            ChannelSpec(
                "channel:pakistan_chat",
                "🇵🇰-pakistan-chat",
                "text",
                topic="Chat for Pakistan-based members. | پاکستانی اراکین کے لیے گپ شپ۔",
            ),
            ChannelSpec(
                "channel:memes",
                "😂-memes",
                "text",
                topic="Memes. | میمز۔",
            ),
            ChannelSpec(
                "channel:clips",
                "🎬-clips",
                "text",
                topic="Share your clips. | اپنی کلپس شیئر کریں۔",
            ),
        ),
    ),
    CategorySpec(
        logical_key="category:brawlhalla",
        name="⚔️ BRAWLHALLA",
        gated=True,  # hidden until manually verified — docs/DECISIONS.md ADR-069
        channels=(
            ChannelSpec(
                "channel:brawlhalla",
                "🎮-brawlhalla",
                "text",
                topic="General Brawlhalla talk. | براولہلا پر عمومی گفتگو۔",
            ),
            ChannelSpec(
                "channel:tips_guides",
                "🧠-tips-guides",
                "text",
                topic="Tips and guides. | تجاویز اور گائیڈز۔",
            ),
            ChannelSpec(
                "channel:legend_talk",
                "🐺-legend-talk",
                "text",
                topic="Legend picks and matchups. | لیجنڈ کا انتخاب اور مقابلے۔",
            ),
            ChannelSpec(
                "channel:one_v_one",
                "⚔️-1v1",
                "text",
                topic="Coordinate 1v1s. | ون-وی-ون کوآرڈینیٹ کریں۔",
            ),
            ChannelSpec(
                "channel:two_v_two",
                "👥-2v2",
                "text",
                topic="Coordinate 2v2s. | ٹو-وی-ٹو کوآرڈینیٹ کریں۔",
            ),
            ChannelSpec(
                "channel:ranked",
                "🏆-ranked",
                "text",
                topic="Looking for a spar? Post here. | اسپار ڈھونڈ رہے ہیں؟ یہاں پوسٹ کریں۔",
            ),
        ),
    ),
    CategorySpec(
        logical_key="category:shaheen_arena",
        name="🏟️ SHAHEEN ARENA",
        restricted=True,  # hidden/disabled from public users until there is a need
        channels=(
            ChannelSpec(
                "channel:scrims",
                "⚔️-scrims",
                "text",
                topic="Scrim announcements. | اسکرم کے اعلانات۔",
            ),
            ChannelSpec(
                "channel:tournaments",
                "🏆-tournaments",
                "text",
                topic="Tournament brackets. | ٹورنامنٹ بریکٹس۔",
            ),
            ChannelSpec(
                "channel:leaderboard",
                "📊-leaderboard",
                "text",
                topic="Clan standings. | کلان کی درجہ بندی۔",
            ),
            ChannelSpec(
                "channel:hall_of_fame",
                "🥇-hall-of-fame",
                "text",
                topic="Milestones and achievements. | کارنامے اور کامیابیاں۔",
            ),
        ),
    ),
    CategorySpec(
        logical_key="category:voice",
        name="🎙️ VOICE",
        gated=True,  # hidden until manually verified — docs/DECISIONS.md ADR-069
        channels=(
            ChannelSpec("channel:voice_the_nest", "🔊-the-nest", "voice"),
            ChannelSpec("channel:voice_gaming", "🎮-gaming", "voice"),
            ChannelSpec("channel:voice_ranked", "⚔️-ranked", "voice"),
            ChannelSpec("channel:voice_afk", "💤-afk", "voice"),
        ),
    ),
    CategorySpec(
        logical_key="category:moderation",
        name="🛡️ MODERATION",
        restricted=True,  # staff-only — ROLES_WITH_STAFF_ACCESS (docs/DECISIONS.md ADR-065)
        channels=(
            ChannelSpec(
                "channel:mod_log",
                "🛡️-mod-log",
                "text",
                topic="Moderation action log — staff only. | نگرانی کا ریکارڈ — صرف اسٹاف کے لیے۔",
            ),
        ),
    ),
    CategorySpec(
        logical_key="category:development",
        name="🛠️ DEVELOPMENT",
        restricted=True,  # admin-only
        channels=(
            ChannelSpec(
                "channel:bot_testing",
                "🤖-bot-testing",
                "text",
                topic="Test bot commands here. | یہاں بوٹ کمانڈز ٹیسٹ کریں۔",
            ),
            ChannelSpec(
                "channel:website_testing",
                "🌐-website-testing",
                "text",
                topic="Website testing. | ویب سائٹ ٹیسٹنگ۔",
            ),
            ChannelSpec(
                "channel:commands",
                "🧪-commands",
                "text",
                topic="Try out commands. | کمانڈز آزمائیں۔",
            ),
            ChannelSpec(
                "channel:bug_reports",
                "🐛-bug-reports",
                "text",
                topic="Report bugs. | بگز رپورٹ کریں۔",
            ),
            ChannelSpec(
                "channel:development_log",
                "📝-development-log",
                "text",
                topic="Dev changelog. | ڈیو چینج لاگ۔",
            ),
        ),
    ),
)
