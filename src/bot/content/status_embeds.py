"""The /admin status embed (docs/DECISIONS.md ADR-129). Pure builder."""

from __future__ import annotations

import discord

from bot.palette import EMERALD
from services.status_service import SystemStatus, format_age

FOOTER = "BRAWLISTAN · system status"
_WARN = 0xE0A030
_DOWN = 0xD9534F


def _tick(ok: bool) -> str:
    return "🟢" if ok else "🔴"


def build_status_embed(status: SystemStatus) -> discord.Embed:
    problems = status.problems()
    if not status.database_ok:
        colour, headline = _DOWN, "🔴 Something is down"
    elif problems:
        colour, headline = _WARN, "🟡 Running, with warnings"
    else:
        colour, headline = EMERALD, "🟢 All systems normal"

    embed = discord.Embed(title="BRAWLISTAN status", description=f"**{headline}**", colour=colour)

    bot = status.bot
    embed.add_field(
        name="Bot",
        value=f"Discord latency **{bot.gateway_ms} ms**\nUp for **{format_age(bot.uptime)}**",
        inline=True,
    )
    if status.database_ok:
        database = (
            f"{_tick(True)} Reachable, **{status.database_ms} ms**\n"
            f"Schema `{status.schema_revision or 'unknown'}`"
        )
    else:
        database = f"{_tick(False)} Unreachable"
    embed.add_field(name="Database", value=database, inline=True)

    age = status.snapshot_age
    if age is None:
        snapshot = "None yet"
    else:
        at = status.last_snapshot_at
        stamp = discord.utils.format_dt(at, "R") if at else ""
        snapshot = f"{format_age(age)} ago {stamp}".strip()
    tracked = "—" if status.tracked_players is None else f"{status.tracked_players:,}"
    embed.add_field(
        name="Rankings",
        value=f"Last snapshot: **{snapshot}**\nEvery {format_age(status.snapshot_interval)}"
        f" · **{tracked}** players tracked",
        inline=False,
    )

    if bot.loops:
        embed.add_field(
            name="Background loops",
            value="\n".join(f"{_tick(running)} {name}" for name, running in bot.loops.items()),
            inline=False,
        )
    if problems:
        embed.add_field(
            name="⚠️ Needs attention", value="\n".join(f"• {p}" for p in problems), inline=False
        )
    embed.set_footer(text=FOOTER)
    return embed
