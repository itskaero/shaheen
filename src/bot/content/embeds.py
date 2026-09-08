"""Branded embeds (docs/BRAND.md): short headings, clear hierarchy, restrained
emoji, green/gold identity, concise copy.
"""

from __future__ import annotations

import discord

from bot.palette import FOREST_GREEN, GOLD
from core.brand import MOTTO, TAGLINE
from services.setup_planner import ActionType, CategoryAction, ChannelAction, RoleAction, SetupPlan
from services.setup_service import ActionSummary, SetupReport


def build_welcome_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🦅 Welcome to Shaheen",
        description=(
            f"**{MOTTO}**\n{TAGLINE}\n\n"
            "Shaheen is a Pakistan-based Brawlhalla clan built around ambition, "
            "skill, discipline, and rising above.\n\n"
            "Start in 📜-rules, then check 🎭-roles to get set up."
        ),
        colour=FOREST_GREEN,
    )
    return embed


def build_rules_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📜 Shaheen Rules",
        description=(
            "1. Respect every member — no harassment, hate speech, or discrimination.\n"
            "2. Keep channels on-topic; use 💬-general or 🇵🇰-pakistan-chat for casual chat.\n"
            "3. No spam, self-promotion, or unsolicited links.\n"
            "4. Follow Discord's Terms of Service and Community Guidelines.\n"
            "5. Staff decisions are final; DM a 🛡️ MODERATOR or 👑 SHAHEEN LEADER with concerns."
        ),
        colour=FOREST_GREEN,
    )
    return embed


def build_roles_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎭 Shaheen Roles",
        description=(
            "👑 **SHAHEEN LEADER** — clan leadership\n"
            "🛡️ **MODERATOR** — community moderation\n"
            "🏆 **ELITE SHAHEEN** — top competitive members\n"
            "🦅 **SHAHEEN** — full clan members\n"
            "🎯 **TRIAL SHAHEEN** — members under evaluation\n"
            "🤝 **ALLY** — friends of the clan\n"
            "👀 **GUEST** — everyone else\n\n"
            "Roles are currently assigned by staff. Player-linked roles arrive "
            "with Brawlhalla integration."
        ),
        colour=GOLD,
    )
    return embed


def build_plan_embed(plan: SetupPlan, mode: str) -> discord.Embed:
    """Preview embed shown before /setup run applies anything."""
    counts = _tally(plan)
    embed = discord.Embed(
        title="🦅 Shaheen Setup — Preview",
        description=f"Mode: **{mode}**\nReview the planned changes, then confirm.",
        colour=GOLD,
    )
    embed.add_field(
        name="Roles",
        value=_count_line(counts["roles"]),
        inline=True,
    )
    embed.add_field(
        name="Categories",
        value=_count_line(counts["categories"]),
        inline=True,
    )
    embed.add_field(
        name="Channels",
        value=_count_line(counts["channels"]),
        inline=True,
    )
    if not plan.has_changes:
        embed.add_field(
            name="Result",
            value="Everything already matches — this run will only verify.",
            inline=False,
        )
    return embed


def build_report_embed(report: SetupReport) -> discord.Embed:
    embed = discord.Embed(
        title="🦅 Shaheen Setup — Report",
        description=f"Mode: **{report.mode}**",
        colour=GOLD if not report.errors else 0xB00020,
    )
    embed.add_field(name="Roles", value=_summary_line(report.roles), inline=True)
    embed.add_field(name="Categories", value=_summary_line(report.categories), inline=True)
    embed.add_field(name="Channels", value=_summary_line(report.channels), inline=True)

    if report.warnings:
        embed.add_field(
            name="⚠️ Warnings", value="\n".join(f"- {w}" for w in report.warnings[:10]), inline=False
        )
    if report.errors:
        embed.add_field(
            name="❌ Errors", value="\n".join(f"- {e}" for e in report.errors[:10]), inline=False
        )
    if not report.warnings and not report.errors:
        embed.add_field(name="Status", value="✅ Completed with no issues.", inline=False)
    return embed


def build_verify_embed(plan: SetupPlan) -> discord.Embed:
    """Itemized discrepancy report for /setup verify."""
    embed = discord.Embed(title="🦅 Shaheen Setup — Verification", colour=GOLD)
    discrepancies: list[RoleAction | CategoryAction | ChannelAction] = [
        a for a in plan.role_actions if a.type is not ActionType.VERIFY
    ]
    discrepancies += [a for a in plan.category_actions if a.type is not ActionType.VERIFY]
    discrepancies += [a for a in plan.channel_actions if a.type is not ActionType.VERIFY]

    if not discrepancies:
        embed.description = "✅ Everything matches the expected Shaheen structure."
        return embed

    noun = "discrepancy" if len(discrepancies) == 1 else "discrepancies"
    embed.description = f"Found {len(discrepancies)} {noun}."
    lines = []
    for action in discrepancies[:20]:
        detail = "; ".join(action.diffs) if action.diffs else ""
        suffix = f" ({detail})" if detail else ""
        lines.append(f"**{action.type.value}** — {action.spec.name}{suffix}")
    embed.add_field(name="Discrepancies", value="\n".join(lines), inline=False)
    if len(discrepancies) > 20:
        embed.set_footer(text=f"...and {len(discrepancies) - 20} more.")
    return embed


def build_status_embed(
    plan: SetupPlan, *, mode: str | None, last_setup_at: str | None
) -> discord.Embed:
    counts = _tally(plan)
    embed = discord.Embed(
        title="🦅 Shaheen Setup — Status",
        colour=FOREST_GREEN,
    )
    embed.add_field(name="Current mode", value=mode or "not run yet", inline=True)
    embed.add_field(name="Last setup", value=last_setup_at or "never", inline=True)
    embed.add_field(name="Roles", value=_count_line(counts["roles"]), inline=True)
    embed.add_field(name="Categories", value=_count_line(counts["categories"]), inline=True)
    embed.add_field(name="Channels", value=_count_line(counts["channels"]), inline=True)
    return embed


def _tally(plan: SetupPlan) -> dict[str, dict[ActionType, int]]:
    def tally_actions(
        actions: tuple[RoleAction, ...] | tuple[CategoryAction, ...] | tuple[ChannelAction, ...],
    ) -> dict[ActionType, int]:
        counts = {t: 0 for t in ActionType}
        for action in actions:
            counts[action.type] += 1
        return counts

    return {
        "roles": tally_actions(plan.role_actions),
        "categories": tally_actions(plan.category_actions),
        "channels": tally_actions(plan.channel_actions),
    }


def _count_line(counts: dict[ActionType, int]) -> str:
    return (
        f"✅ {counts[ActionType.VERIFY]} matching\n"
        f"🆕 {counts[ActionType.CREATE]} to create\n"
        f"🔧 {counts[ActionType.REPAIR]} to repair\n"
        f"🔗 {counts[ActionType.ADOPT]} to adopt"
    )


def _summary_line(summary: ActionSummary) -> str:
    return (
        f"✅ {summary.verified} verified\n"
        f"🆕 {len(summary.created)} created\n"
        f"🔧 {len(summary.repaired)} repaired\n"
        f"🔗 {len(summary.adopted)} adopted"
    )
