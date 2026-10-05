"""Embeds for the BRAWLISTAN network commands (docs/DECISIONS.md ADR-111):
/ping, /site, /rankings, /season, /legend, /tournaments, /report, /announce,
/feature. Pure builders — no Discord state, no database — so they're
testable on their own.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import discord

from bot.palette import CREAM, EMERALD, FOREST_GREEN, GOLD, GREY
from database.models.player_report import PlayerReport
from database.models.tournament import Tournament, TournamentStatus
from services.clan_service import LegendMetaEntry
from services.legend_art import legend_display_name
from services.pakistan_board_service import PakistanClimber
from services.players_service import player_slug
from services.rankings_service import RankingRow
from services.seasons import PakistanSeason, season_label

FOOTER = "BRAWLISTAN · Pakistan's Brawlhalla Network"
_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

# The site's main pages, in the order /site lists them.
SITE_PAGES: tuple[tuple[str, str], ...] = (
    ("Home", "index.html"),
    ("Rankings", "rankings.html"),
    ("Players", "players.html"),
    ("Tournaments", "tournaments.html"),
)


def _place(i: int) -> str:
    return _MEDALS.get(i, f"`{i:>2}`")


def player_url(site_url: str, player_name: str, brawlhalla_id: int) -> str:
    return f"{site_url.rstrip('/')}/player/{player_slug(player_name, brawlhalla_id)}/"


def build_ping_embed(latency_ms: int) -> discord.Embed:
    return discord.Embed(
        title="🏓 Pong", description=f"Gateway latency **{latency_ms} ms**.", colour=EMERALD
    )


def build_site_embed(site_url: str) -> discord.Embed:
    embed = discord.Embed(
        title="BRAWLISTAN on the web",
        url=site_url,
        description="Pakistan rankings, player profiles, seasons and tournaments.",
        colour=FOREST_GREEN,
    )
    embed.set_footer(text=FOOTER)
    return embed


def site_view(site_url: str) -> discord.ui.View:
    """Link buttons only — no callbacks, so nothing to persist."""
    view = discord.ui.View()
    base = site_url.rstrip("/")
    for label, page in SITE_PAGES:
        view.add_item(discord.ui.Button(label=label, url=f"{base}/{page}"))
    return view


def profile_view(site_url: str, player_name: str, brawlhalla_id: int) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="View profile", url=player_url(site_url, player_name, brawlhalla_id), emoji="🔗"
        )
    )
    return view


def build_rankings_embed(
    *,
    rows: Sequence[RankingRow],
    bracket: str,
    season: int | None,
    site_url: str,
    limit: int = 10,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🇵🇰 Pakistan Rankings · {bracket}",
        url=f"{site_url.rstrip('/')}/rankings.html",
        colour=GOLD,
    )
    lines = []
    for i, row in enumerate(rows[:limit], start=1):
        snap = row.snapshot
        rating = snap.rating_2v2 if bracket == "2v2" else snap.rating
        tier = (snap.tier_2v2 if bracket == "2v2" else snap.tier) or "Unranked"
        marks = " ✓" if row.is_verified else ""
        lines.append(f"{_place(i)} **{row.player.player_name}**{marks} — {rating} · {tier}")
    embed.description = "\n".join(lines) if lines else "Data unavailable — nobody is placed yet."
    embed.set_footer(text=season_label(season) or FOOTER)
    return embed


def build_rising_embed(*, climbers: Sequence[PakistanClimber], site_url: str) -> discord.Embed:
    embed = discord.Embed(
        title="📈 Rising this week",
        url=f"{site_url.rstrip('/')}/rankings.html#rising",
        colour=EMERALD,
    )
    lines = [
        f"{_place(i)} **{c.player.player_name}** +{c.rating_gain} → {c.rating}"
        for i, c in enumerate(climbers, start=1)
    ]
    embed.description = "\n".join(lines) if lines else "Data unavailable — no climbs this week yet."
    embed.set_footer(text=FOOTER)
    return embed


def build_season_embed(season: PakistanSeason, *, now: datetime) -> discord.Embed:
    days_left = max(0, (season.ends_at - now).days)
    embed = discord.Embed(
        title=f"Pakistan Season {season.number} · {season.name}",
        description=(
            f"# {season.name_urdu}\n"
            f"Brawlhalla Season {season.brawlhalla_season}\n"
            f"Started {season.starts_at:%d %b %Y} · ends about {season.ends_at:%d %b %Y} "
            f"(**{days_left}** days left)."
        ),
        colour=GOLD,
    )
    embed.set_footer(text="BRAWLISTAN · a new season every 13 weeks")
    return embed


def build_legend_embed(
    entry: LegendMetaEntry | None, *, legend_key: str, rank: int | None
) -> discord.Embed:
    name = legend_display_name(legend_key)
    embed = discord.Embed(title=f"⚔️ {name} in Pakistan", colour=CREAM)
    if entry is None:
        embed.description = "Data unavailable — no tracked player has played this Legend yet."
        return embed
    embed.add_field(name="Players", value=str(entry.player_count), inline=True)
    embed.add_field(name="Games", value=f"{entry.total_games:,}", inline=True)
    embed.add_field(name="Win rate", value=f"{entry.win_rate:.1f}%", inline=True)
    if rank is not None:
        embed.add_field(name="Popularity", value=f"#{rank} across the network", inline=False)
    embed.set_footer(text="Lifetime games of every tracked Pakistani player · " + FOOTER)
    return embed


_STATUS_LABEL = {
    TournamentStatus.REGISTRATION: "🟢 Registration open",
    TournamentStatus.IN_PROGRESS: "🟠 Live",
    TournamentStatus.COMPLETED: "✅ Completed",
    TournamentStatus.CANCELLED: "✖️ Cancelled",
}


def build_tournaments_embed(tournaments: Sequence[Tournament], *, site_url: str) -> discord.Embed:
    embed = discord.Embed(
        title="🏟️ Tournaments",
        url=f"{site_url.rstrip('/')}/tournaments.html",
        colour=GOLD,
    )
    lines = [
        f"**#{t.id} {t.name}** · {t.kind.value} · {_STATUS_LABEL.get(t.status, t.status.value)}"
        for t in tournaments
    ]
    embed.description = (
        "\n".join(lines) if lines else "No tournaments yet. Staff announce them in #tournaments."
    )
    embed.set_footer(text="Enter an open one with /tournament register")
    return embed


def build_player_report_embed(report: PlayerReport, *, reporter: str | None) -> discord.Embed:
    """The #report card (staff-only channel), shared by both sources."""
    embed = discord.Embed(
        title=f"🛡️ Report #{report.id}",
        description=report.reason,
        colour=GREY,
        timestamp=report.created_at,
    )
    reported = report.reported_name
    if report.reported_discord_id is not None:
        reported += f" (<@{report.reported_discord_id}>)"
    if report.reported_brawlhalla_id is not None:
        reported += f" · Brawlhalla {report.reported_brawlhalla_id}"
    embed.add_field(name="Reported", value=reported, inline=False)
    embed.add_field(name="Reporter", value=reporter or "Website visitor", inline=True)
    embed.add_field(name="Source", value=report.source.title(), inline=True)
    embed.add_field(name="Status", value=report.status.title(), inline=True)
    return embed


def build_report_received_embed(report_id: int) -> discord.Embed:
    return discord.Embed(
        title="Report sent",
        description=f"Thanks — staff will review report **#{report_id}**. "
        "Reports are private; the player isn't told who sent it.",
        colour=EMERALD,
    )


def build_announcement_embed(*, title: str, message: str, author: str) -> discord.Embed:
    embed = discord.Embed(title=title, description=message, colour=GOLD)
    embed.set_footer(text=f"{author} · BRAWLISTAN")
    return embed


def build_featured_embed(
    *, player_name: str, note: str | None, site_url: str, brawlhalla_id: int
) -> discord.Embed:
    embed = discord.Embed(
        title=f"⭐ Featured: {player_name}",
        url=player_url(site_url, player_name, brawlhalla_id),
        description=note or "Now featured on the BRAWLISTAN home page.",
        colour=GOLD,
    )
    embed.set_footer(text=FOOTER)
    return embed
