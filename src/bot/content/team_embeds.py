"""Embeds for /team (docs/DECISIONS.md ADR-114). Pure builders."""

from __future__ import annotations

from collections.abc import Sequence

import discord

from bot.palette import GOLD
from services.team_service import RosterEntry, TeamSummary

_SHOWN = 15


def team_url(site_url: str, slug: str) -> str:
    return f"{site_url.rstrip('/')}/team.html?t={slug}"


def build_team_embed(
    summary: TeamSummary, roster: Sequence[RosterEntry], *, site_url: str
) -> discord.Embed:
    team = summary.team
    embed = discord.Embed(
        title=f"{team.name} [{team.tag}]",
        url=team_url(site_url, team.slug),
        description=team.description or None,
        colour=GOLD,
    )
    if team.logo:
        embed.set_thumbnail(url=f"{site_url.rstrip('/')}/assets/img/teams/{team.logo}.png")
    if team.is_founding:
        embed.set_author(name="Founding team of BRAWLISTAN")
    embed.add_field(name="Players", value=str(summary.members), inline=True)
    embed.add_field(
        name="Team rating",
        value=str(summary.rating) if summary.rating is not None else "Data unavailable",
        inline=True,
    )
    lines = []
    for entry in roster[:_SHOWN]:
        crown = "👑 " if entry.member.role == "captain" else ""
        rating = entry.snapshot.rating if entry.snapshot else None
        tier = (entry.snapshot.tier if entry.snapshot else None) or "Unranked"
        lines.append(f"{crown}**{entry.player.player_name}** — {rating or '—'} · {tier}")
    if len(roster) > _SHOWN:
        lines.append(f"…and {len(roster) - _SHOWN} more")
    embed.add_field(
        name="Roster",
        value="\n".join(lines) if lines else "No players yet — staff add them with /team add.",
        inline=False,
    )
    embed.set_footer(text="Team rating = average of the best 3 placed players · BRAWLISTAN")
    return embed


def team_view(site_url: str, slug: str) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Team page", url=team_url(site_url, slug), emoji="🛡️"))
    return view
