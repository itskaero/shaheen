"""Branded embeds for /emoji sync, /emoji browse, and /emoji clear
(docs/DECISIONS.md ADR-090/ADR-092/ADR-094).
"""

from __future__ import annotations

import discord

from bot.palette import EMERALD, GOLD
from services.emoji_service import EmojiClearReport, EmojiSyncReport

_DANGER = 0xB00020


def build_emoji_browse_intro_embed() -> discord.Embed:
    return discord.Embed(
        title="🦅 Shaheen Emoji Pack — Browse",
        description=(
            "Pick a legend below to see its available expressions one at a time. "
            "**➕ Add** queues the one on screen (you'll get to name it); "
            "**✅ Done** uploads everything you've queued."
        ),
        colour=EMERALD,
    )


def build_emoji_candidate_preview_embed(
    *, legend: str, index: int, total: int, queue_count: int
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🦅 {legend.replace('_', ' ').title()} — {index + 1}/{total}",
        colour=EMERALD,
    )
    embed.set_image(url="attachment://preview.png")
    embed.set_footer(text=f"Queued: {queue_count}" + (" — nothing yet" if queue_count == 0 else ""))
    return embed


def build_emoji_sync_embed(report: EmojiSyncReport) -> discord.Embed:
    embed = discord.Embed(
        title="🦅 Shaheen Emoji Pack — Synced",
        description=f"Checked **{report.total}** emoji from the pack.",
        colour=GOLD if not report.errors else 0xB00020,
    )
    embed.add_field(name="🆕 Created", value=str(len(report.created)), inline=True)
    embed.add_field(name="✅ Already present", value=str(len(report.skipped_existing)), inline=True)
    if report.skipped_no_room:
        embed.add_field(name="🚫 No room", value=str(len(report.skipped_no_room)), inline=True)
    if report.created:
        embed.add_field(
            name="New emoji",
            value=" ".join(f"`:{name}:`" for name in report.created[:25]),
            inline=False,
        )
    if report.skipped_no_room:
        embed.add_field(
            name="Skipped — no free slots",
            value=(
                "This server is out of static emoji slots. Boost the server or remove some "
                "unused emoji, then run `/emoji sync` again.\n"
                + ", ".join(f"`{name}`" for name in report.skipped_no_room[:15])
            ),
            inline=False,
        )
    if report.errors:
        embed.add_field(
            name="❌ Errors", value="\n".join(f"- {e}" for e in report.errors[:10]), inline=False
        )
    if not report.created and not report.skipped_no_room and not report.errors:
        embed.add_field(
            name="Status", value="Every packaged emoji is already on this server.", inline=False
        )
    return embed


def build_emoji_clear_warning_embed() -> discord.Embed:
    return discord.Embed(
        title="⚠️ Confirm: Delete ALL Custom Emoji",
        description=(
            "This deletes **every custom emoji in this server** — including anything staff "
            "added by hand, not just the Shaheen pack. This cannot be undone; anything removed "
            "would need to be re-uploaded (the pack can be restored with `/emoji sync`, but "
            "anything else is gone for good)."
        ),
        colour=_DANGER,
    )


def build_emoji_clear_report_embed(report: EmojiClearReport) -> discord.Embed:
    embed = discord.Embed(
        title="🗑️ Shaheen Emoji Pack — Cleared",
        description=f"Checked **{report.total}** emoji on this server.",
        colour=GOLD if not report.errors else _DANGER,
    )
    embed.add_field(name="🗑️ Deleted", value=str(len(report.deleted)), inline=True)
    if report.deleted:
        embed.add_field(
            name="Removed",
            value=" ".join(f"`:{name}:`" for name in report.deleted[:25]),
            inline=False,
        )
    if report.errors:
        embed.add_field(
            name="❌ Errors", value="\n".join(f"- {e}" for e in report.errors[:10]), inline=False
        )
    if not report.deleted and not report.errors:
        embed.add_field(name="Status", value="No custom emoji found on this server.", inline=False)
    return embed
