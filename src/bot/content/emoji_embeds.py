"""Branded embed for /emoji sync (docs/DECISIONS.md ADR-090)."""

from __future__ import annotations

import discord

from bot.palette import GOLD
from services.emoji_service import EmojiSyncReport


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
