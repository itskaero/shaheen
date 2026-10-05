"""Branded embeds (docs/BRAND.md): short headings, clear hierarchy, restrained
emoji, green/gold identity, concise copy.
"""

from __future__ import annotations

import discord

from bot.constants import ROLE_ADMIN, ROLE_FOUNDER, ROLE_MODERATOR
from bot.palette import FOREST_GREEN, GOLD
from database.models.provisioned_resource import ResourceType
from services.setup_planner import ActionType, CategoryAction, ChannelAction, RoleAction, SetupPlan
from services.setup_service import ActionSummary, ResetReport, RetiredResource, SetupReport

_DANGER = 0xB00020


def build_welcome_embed() -> discord.Embed:
    return discord.Embed(
        title="Welcome to BRAWLISTAN",
        description=(
            "**Pakistan's Brawlhalla Network.**\n"
            "Track the scene. Find the players. Climb the rankings.\n\n"
            "1. Read #rules.\n"
            "2. Run `/link` in #bot-commands to put your Brawlhalla account on the Pakistan "
            "rankings — you'll get the **Player** role.\n"
            "3. Find a game in #looking-for-game.\n\n"
            "BRAWLISTAN grew out of SHAHEEN, its founding team."
        ),
        colour=FOREST_GREEN,
    )


def build_rules_embed() -> discord.Embed:
    return discord.Embed(
        title="📜 Rules",
        description=(
            "1. Respect every player — no harassment, hate speech or discrimination.\n"
            "2. Keep channels on-topic; casual chat goes in #general.\n"
            "3. No spam, self-promotion or unsolicited links.\n"
            "4. Don't impersonate players or claim an account that isn't yours.\n"
            "5. Follow Discord's Terms of Service and Community Guidelines.\n"
            "6. Report problems with `/report` — don't call people out in public.\n"
            f"7. Staff decisions are final; DM a **{ROLE_MODERATOR.name}**, "
            f"**{ROLE_ADMIN.name}** or the **{ROLE_FOUNDER.name}** with concerns."
        ),
        colour=FOREST_GREEN,
    )


def build_plan_embed(plan: SetupPlan, mode: str) -> discord.Embed:
    """Preview embed shown before /setup run applies anything."""
    counts = _tally(plan)
    embed = discord.Embed(
        title="BRAWLISTAN Setup — Preview",
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
    embed.set_footer(text="Setup never changes role or channel permissions — you set those.")
    return embed


def build_report_embed(report: SetupReport) -> discord.Embed:
    embed = discord.Embed(
        title="BRAWLISTAN Setup — Report",
        description=f"Mode: **{report.mode}**" if report.mode else "Roles only.",
        colour=GOLD if not report.errors else _DANGER,
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


def build_reset_warning_embed() -> discord.Embed:
    """Shown before the type-DELETE-to-confirm modal (docs/DECISIONS.md
    ADR-060) — /setup reset is permanent and unrelated to the normal,
    safe /setup run flow.
    """
    return discord.Embed(
        title="⚠️ Reset the server structure?",
        description=(
            "This permanently **deletes every role, category, and channel** "
            "`/setup` has ever created — including all messages in them. "
            "This cannot be undone.\n\n"
            "Stored member/player/match/achievement data is **not** affected — "
            "only the Discord structure itself.\n\n"
            "This is a separate, deliberately destructive command — `/setup run` "
            "remains safe to re-run any time and never deletes anything."
        ),
        colour=_DANGER,
    )


def build_reset_report_embed(report: ResetReport) -> discord.Embed:
    embed = discord.Embed(
        title="🗑️ BRAWLISTAN Setup — Reset Complete",
        description=f"Deleted **{report.total_deleted}** resource(s).",
        colour=GOLD if not report.errors else _DANGER,
    )
    embed.add_field(name="Roles deleted", value=str(report.roles_deleted), inline=True)
    embed.add_field(name="Categories deleted", value=str(report.categories_deleted), inline=True)
    embed.add_field(name="Channels deleted", value=str(report.channels_deleted), inline=True)
    if report.errors:
        embed.add_field(
            name="❌ Errors", value="\n".join(f"- {e}" for e in report.errors[:10]), inline=False
        )
    embed.add_field(
        name="Next step", value="Run `/setup run` to rebuild from scratch.", inline=False
    )
    return embed


def build_verify_embed(plan: SetupPlan) -> discord.Embed:
    """Itemized discrepancy report for /setup verify."""
    embed = discord.Embed(title="BRAWLISTAN Setup — Verification", colour=GOLD)
    discrepancies: list[RoleAction | CategoryAction | ChannelAction] = [
        a for a in plan.role_actions if a.type is not ActionType.VERIFY
    ]
    discrepancies += [a for a in plan.category_actions if a.type is not ActionType.VERIFY]
    discrepancies += [a for a in plan.channel_actions if a.type is not ActionType.VERIFY]

    if not discrepancies:
        embed.description = "✅ Everything matches the expected BRAWLISTAN structure."
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
        title="BRAWLISTAN Setup — Status",
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


_KIND_LABEL = {
    ResourceType.ROLE: "Role",
    ResourceType.CATEGORY: "Category",
    ResourceType.CHANNEL: "Channel",
}


def build_restructure_preview_embed(retired: list[RetiredResource]) -> discord.Embed:
    """What /setup restructure would delete (docs/DECISIONS.md ADR-109)."""
    if not retired:
        return discord.Embed(
            title="BRAWLISTAN Setup — Restructure",
            description="✅ Nothing to remove: every resource setup created is in the "
            "BRAWLISTAN layout.",
            colour=FOREST_GREEN,
        )
    present = [r for r in retired if r.name is not None]
    lines = [f"**{_KIND_LABEL[r.resource_type]}** — {r.name}" for r in present[:25]]
    if len(present) > 25:
        lines.append(f"…and {len(present) - 25} more.")
    gone = len(retired) - len(present)
    embed = discord.Embed(
        title="⚠️ Remove the old SHAHEEN structure?",
        description=(
            f"Deletes **{len(present)}** role(s)/channel(s) that `/setup` created for the old "
            "SHAHEEN layout and that BRAWLISTAN no longer uses — including every message in "
            "those channels. This cannot be undone.\n\n"
            "Only resources setup itself created are listed; anything you made by hand is "
            "never touched. Stored player, ranking and match data is not affected."
        ),
        colour=_DANGER,
    )
    embed.add_field(name="Will be deleted", value="\n".join(lines) or "—", inline=False)
    embed.add_field(
        name="Afterwards",
        value=(
            "Channels carried over from SHAHEEN (#rankings, #looking-for-game, "
            "#achievements, #bot-commands and others) keep their old permission "
            "settings, and setup won't change them. Check each one, or use "
            "**Sync Now** with its category."
        ),
        inline=False,
    )
    if gone:
        embed.set_footer(text=f"{gone} already deleted by hand; they'll just be forgotten.")
    return embed


def build_restructure_report_embed(report: ResetReport) -> discord.Embed:
    embed = discord.Embed(
        title="🗑️ BRAWLISTAN Setup — Restructure Complete",
        description=f"Deleted **{report.total_deleted}** old resource(s).",
        colour=GOLD if not report.errors else _DANGER,
    )
    embed.add_field(name="Roles", value=str(report.roles_deleted), inline=True)
    embed.add_field(name="Categories", value=str(report.categories_deleted), inline=True)
    embed.add_field(name="Channels", value=str(report.channels_deleted), inline=True)
    if report.errors:
        embed.add_field(
            name="❌ Errors", value="\n".join(f"- {e}" for e in report.errors[:10]), inline=False
        )
    return embed
