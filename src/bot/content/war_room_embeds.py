"""War room posts (docs/DECISIONS.md ADR-136): the live scoreboard, lead
changes, the final-hours countdown and the Monday verdict."""

from __future__ import annotations

from datetime import datetime

import discord

from services.cities import CityStanding
from services.clan_war_service import TeamWeek, WarWeek
from services.clan_wars import TEAM_TOP_N, WIN_POINTS

EMBER = 0xFF6A1F
FIRE = 0xFF2E3A
GOLD = 0xF2C14E
_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def _place(i: int) -> str:
    return _MEDALS.get(i, f"`{i}.`")


def _week_label(week: WarWeek) -> str:
    return week.week_start.strftime("%-d %b")


def _team_label(team_week: TeamWeek | None, fallback: str = "—") -> str:
    if team_week is None:
        return fallback
    return f"**{team_week.team.name}** [{team_week.team.tag}]"


def duel_lines(week: WarWeek, *, finished: bool = False) -> list[str]:
    lines = []
    for duel in week.duels:
        a = week.team(duel.team_a)
        if duel.team_b is None:
            lines.append(f"😴 {_team_label(a)} has a bye this week")
            continue
        b = week.team(duel.team_b)
        if duel.winner is None:
            mark = "🤝" if finished and duel.points_a else "⚔️"
        else:
            mark = "🏆" if finished else "🔥"
        lines.append(
            f"{mark} {_team_label(a)} **{duel.points_a}** — **{duel.points_b}** {_team_label(b)}"
        )
    return lines


def build_scoreboard_embed(
    *, week: WarWeek, cities: list[CityStanding], site_url: str, now: datetime
) -> discord.Embed:
    """The pinned live scoreboard, edited every tick."""
    site = site_url.rstrip("/")
    embed = discord.Embed(
        title=f"⚔️ WAR ROOM · week of {_week_label(week)}",
        url=f"{site}/clanwars.html",
        colour=EMBER,
        description=(
            f"Ends <t:{int(week.ends_at.timestamp())}:R> · Monday 00:00 PKT\n"
            f"Updated <t:{int(now.timestamp())}:R> from ranked play"
        ),
    )
    duels = duel_lines(week)
    if duels:
        embed.add_field(name="This week's duels", value="\n".join(duels)[:1024], inline=False)
    standings = [
        f"{_place(i)} {_team_label(t)} — **{t.points}** pts"
        + (f" · {', '.join(s.player.player_name for s in t.counted[:2])}" if t.counted else "")
        for i, t in enumerate(week.standings[:8], start=1)
    ]
    embed.add_field(
        name="🛡️ Clan Wars",
        value="\n".join(standings)[:1024] if standings else "No teams yet.",
        inline=False,
    )
    mvp = week.mvp
    if mvp is not None:
        team = f" [{mvp.team.tag}]" if mvp.team else ""
        embed.add_field(
            name="⭐ Top scorer", value=f"**{mvp.player.player_name}**{team} — {mvp.points} pts"
        )
    if cities:
        city_lines = [
            f"{_place(i)} **{c.label}** — {c.rating:,} ({c.players} placed)"
            for i, c in enumerate(cities[:5], start=1)
        ]
        embed.add_field(name="🏙️ City Wars", value="\n".join(city_lines), inline=False)
    embed.add_field(
        name="Get in the fight",
        value="Link your account in #welcome · pick your city with `/city set` · play ranked.",
        inline=False,
    )
    embed.set_footer(
        text=f"{WIN_POINTS} pts per ranked win + every rating point gained · best {TEAM_TOP_N} "
        "count · rosters lock at week start"
    )
    return embed


def build_lead_change_text(*, week: WarWeek, old_leader: int, new_leader: int) -> str:
    new = week.team(new_leader)
    old = week.team(old_leader)
    if new is None:
        return ""
    gap = new.points - (old.points if old else 0)
    rival = old.team.name if old else "the field"
    return (
        f"⚔️ **{new.team.name}** just took the lead from **{rival}**! "
        f"{new.points} pts, {gap} clear. War ends <t:{int(week.ends_at.timestamp())}:R>."
    )


def build_countdown_embed(*, week: WarWeek, site_url: str) -> discord.Embed:
    embed = discord.Embed(
        title="⏳ Final hours of Clan Wars",
        url=f"{site_url.rstrip('/')}/clanwars.html",
        colour=FIRE,
        description=(
            f"The week ends <t:{int(week.ends_at.timestamp())}:R>. Every ranked win is "
            f"**{WIN_POINTS} points** for your clan. Duels can still flip:"
        ),
    )
    duels = duel_lines(week)
    if duels:
        embed.add_field(name="Duels", value="\n".join(duels)[:1024], inline=False)
    return embed


def build_verdict_embed(*, week: WarWeek, site_url: str, mvp_mention: str | None) -> discord.Embed:
    winner = week.standings[0] if week.standings and week.standings[0].points > 0 else None
    embed = discord.Embed(
        title=(f"🏆 {winner.team.name} win the week!" if winner else "Clan Wars: the week is over"),
        url=f"{site_url.rstrip('/')}/clanwars.html",
        colour=GOLD,
        description=f"Week of {_week_label(week)} · final standings",
    )
    embed.add_field(
        name="Standings",
        value="\n".join(
            f"{_place(i)} {_team_label(t)} — **{t.points}** pts"
            for i, t in enumerate(week.standings[:8], start=1)
        )
        or "Nobody scored.",
        inline=False,
    )
    duels = duel_lines(week, finished=True)
    if duels:
        embed.add_field(name="Duels", value="\n".join(duels)[:1024], inline=False)
    mvp = week.mvp
    if mvp is not None:
        who = mvp_mention or f"**{mvp.player.player_name}**"
        team = f" for **{mvp.team.name}**" if mvp.team else ""
        embed.add_field(name="⭐ MVP of the week", value=f"{who} — {mvp.points} pts{team}")
    embed.set_footer(text="A new war has begun. Share the card with your clan.")
    embed.set_image(url="attachment://clan-wars.png")
    return embed
