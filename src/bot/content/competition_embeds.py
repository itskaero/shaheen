"""Branded embeds for /challenge, /scrim, /match (incl. /match report), /matches, /tournament."""

from __future__ import annotations

from datetime import datetime

import discord

from bot.palette import EMERALD, FOREST_GREEN, GOLD, GREY
from database.models.match import Match, MatchKind, MatchStatus
from database.models.tournament import Tournament, TournamentMatch, TournamentMatchStatus
from services.legend_art import legend_display_name, legend_portrait_path, normalize_legend_key
from services.spar_service import SparProfile

# BRAWLISTAN orange, as on the link panel: spar cards should pop in the feed.
SPAR_ORANGE = 0xFF6A1F


def build_spar_kiosk_embed() -> discord.Embed:
    """Posted with SparKioskView attached (bot/cogs/setup.py, docs/DECISIONS.md
    ADR-058, ADR-136) — the 1v1/2v2 buttons run the same flow as /looking.
    """
    embed = discord.Embed(
        title="🥊 Looking for a game?",
        description=(
            "Tap a mode and BRAWLISTAN posts a spar card here with your rating and main, "
            "a Join button, and a ping for everyone with **Spar Ping**.\n\n"
            "🔔 **Spar pings**: get tagged whenever someone's looking. Tap again to stop."
        ),
        colour=SPAR_ORANGE,
    )
    embed.add_field(name="Add a note", value="`/looking mode:1v1 note:FT5, NA`", inline=True)
    embed.add_field(name="Pick a rival", value="`/challenge @member`", inline=True)
    embed.set_footer(text="Cards close after 30 minutes. Pings go out at most every 10 minutes.")
    return embed


def build_challenge_embed(*, challenger_name: str, opponent_name: str) -> discord.Embed:
    return discord.Embed(
        title="⚔️ Challenge",
        description=f"**{challenger_name}** has challenged **{opponent_name}** to a 1v1!",
        colour=GOLD,
    )


def build_challenge_result_embed(*, accepted: bool, opponent_name: str) -> discord.Embed:
    if accepted:
        return discord.Embed(
            title="✅ Challenge Accepted",
            description=(
                f"**{opponent_name}** accepted. Good luck — report the result with `/match report`."
            ),
            colour=FOREST_GREEN,
        )
    return discord.Embed(
        title="Challenge Declined",
        description=f"**{opponent_name}** declined the challenge.",
        colour=GREY,
    )


def _slots(names: list[str], capacity: int) -> str:
    filled = [f"🟢 {name}" for name in names[:capacity]]
    return "\n".join(filled + ["⚪ *open*"] * (capacity - len(filled)))


def _profile_line(profile: SparProfile) -> str:
    name = (
        f"**[{profile.team_tag}] {profile.player_name}**"
        if profile.team_tag
        else (f"**{profile.player_name}**")
    )
    bits = [name]
    if profile.rating is not None:
        bits.append(f"1v1 **{profile.rating:,}**" + (f" {profile.tier}" if profile.tier else ""))
    if profile.rating_2v2 is not None:
        bits.append(f"2v2 **{profile.rating_2v2:,}**")
    if profile.region:
        bits.append(f"🌍 {profile.region.upper()}")
    if profile.city:
        bits.append(f"🏙️ {profile.city}")
    return " · ".join(bits)


def build_scrim_embed(
    *,
    creator_name: str,
    kind: MatchKind,
    side_counts: tuple[int, int],
    sides: tuple[list[str], list[str]] | None = None,
    profile: SparProfile | None = None,
    note: str | None = None,
    expires_at: datetime | None = None,
    site_url: str | None = None,
) -> discord.Embed:
    """The spar card (ADR-136): who's looking, at what level, open slots."""
    capacity = 1 if kind is MatchKind.ONE_V_ONE else 2
    a_names, b_names = sides if sides is not None else ([], [])
    a_count, b_count = side_counts
    lines = []
    if note:
        lines.append(f"> {note}")
    lines.append(
        _profile_line(profile)
        if profile
        else f"**{creator_name}** · not linked yet (`/link` to show your rating)"
    )
    if expires_at is not None:
        stamp = int(expires_at.timestamp())
        lines.append(f"⏳ Open until <t:{stamp}:t> (<t:{stamp}:R>)")
    embed = discord.Embed(
        title=f"🥊 {creator_name} is looking for a {kind.value}",
        description="\n".join(lines),
        colour=SPAR_ORANGE,
    )
    # Names when the caller tracks them, else counts (older callers).
    embed.add_field(
        name="Side A",
        value=_slots(a_names, capacity) if sides is not None else f"{a_count}/{capacity}",
        inline=True,
    )
    embed.add_field(
        name="Side B",
        value=_slots(b_names, capacity) if sides is not None else f"{b_count}/{capacity}",
        inline=True,
    )
    if profile and profile.main_legend and site_url and legend_portrait_path(profile.main_legend):
        key = normalize_legend_key(profile.main_legend)
        embed.set_thumbnail(url=f"{site_url.rstrip('/')}/assets/img/legend-portraits/{key}.webp")
        embed.set_footer(text=f"Main: {legend_display_name(profile.main_legend)}")
    return embed


def build_scrim_full_embed(
    *, kind: MatchKind, sides: tuple[list[str], list[str]] | None = None
) -> discord.Embed:
    embed = discord.Embed(
        title=f"✅ {kind.value} locked in",
        description="Good luck! Report the result with `/match report` when you're done.",
        colour=FOREST_GREEN,
    )
    if sides is not None:
        embed.add_field(name="Side A", value="\n".join(sides[0]) or "—", inline=True)
        embed.add_field(name="Side B", value="\n".join(sides[1]) or "—", inline=True)
    return embed


def build_scrim_closed_embed(
    *, creator_name: str, kind: MatchKind, cancelled: bool
) -> discord.Embed:
    return discord.Embed(
        title=f"{creator_name}'s {kind.value} call {'was cancelled' if cancelled else 'expired'}",
        description="Still up for a game? Tap the spar panel or use `/looking` again.",
        colour=GREY,
    )


def build_report_preview_embed(*, reporter_name: str, claim: str) -> discord.Embed:
    return discord.Embed(
        title="📋 Result Reported",
        description=f"**{reporter_name}** reported: **{claim}**.\nThe other side needs to confirm.",
        colour=GOLD,
    )


def build_report_outcome_embed(*, confirmed: bool) -> discord.Embed:
    if confirmed:
        return discord.Embed(
            title="✅ Result Confirmed",
            description="The match result is now final.",
            colour=FOREST_GREEN,
        )
    return discord.Embed(
        title="⚠️ Result Disputed",
        description="A Moderator or Admin will need to resolve this with `/match resolve`.",
        colour=GOLD,
    )


def build_match_embed(
    *, match: Match, side_a_names: list[str], side_b_names: list[str]
) -> discord.Embed:
    embed = discord.Embed(title=f"Match #{match.id} — {match.kind.value}", colour=EMERALD)
    embed.add_field(name="Side A", value=", ".join(side_a_names) or "—", inline=True)
    embed.add_field(name="Side B", value=", ".join(side_b_names) or "—", inline=True)
    status_line = match.status.value.replace("_", " ").title()
    if match.status is MatchStatus.CONFIRMED and match.winning_side:
        status_line += f" — Side {match.winning_side.value} won"
    embed.add_field(name="Status", value=status_line, inline=False)
    return embed


def build_match_history_embed(*, display_name: str, matches: list[Match]) -> discord.Embed:
    embed = discord.Embed(title=f"📜 {display_name} — Match History", colour=EMERALD)
    if not matches:
        embed.description = "No matches recorded yet."
        return embed
    lines = []
    for match in matches:
        outcome = "confirmed" if match.status is MatchStatus.CONFIRMED else match.status.value
        lines.append(f"Match #{match.id} ({match.kind.value}) — {outcome}")
    embed.description = "\n".join(lines)
    return embed


def build_rivalry_embed(
    *, name_a: str, name_b: str, member_a_wins: int, member_b_wins: int, total_matches: int
) -> discord.Embed:
    """docs/DECISIONS.md ADR-068 — head-to-head record from Shaheen's own
    tracked matches, purely internal, no Brawlhalla API involvement.
    """
    embed = discord.Embed(title=f"⚔️ {name_a} vs {name_b}", colour=GOLD)
    if total_matches == 0:
        embed.description = f"**{name_a}** and **{name_b}** haven't played a tracked match yet."
        return embed

    embed.add_field(name=name_a, value=f"{member_a_wins}W", inline=True)
    embed.add_field(name=name_b, value=f"{member_b_wins}W", inline=True)
    embed.set_footer(text=f"{total_matches} confirmed match(es) between them")
    return embed


def build_tournament_created_embed(*, tournament: Tournament) -> discord.Embed:
    return discord.Embed(
        title=f"🏆 {tournament.name}",
        description=(
            f"A {tournament.kind.value} tournament is open for registration.\n"
            "Use `/tournament register` to join."
        ),
        colour=GOLD,
    )


def build_bracket_embed(
    *, tournament: Tournament, rounds: dict[int, list[tuple[TournamentMatch, str, str]]]
) -> discord.Embed:
    """`rounds`: round_number -> [(bracket_match, entrant_a_label, entrant_b_label), ...]"""
    embed = discord.Embed(title=f"🏆 {tournament.name} — Bracket", colour=GOLD)
    for round_number in sorted(rounds):
        lines = []
        for bracket_match, a_label, b_label in rounds[round_number]:
            resolved = (TournamentMatchStatus.COMPLETED, TournamentMatchStatus.BYE)
            marker = "✅" if bracket_match.status in resolved else "⏳"
            lines.append(f"{marker} {a_label} vs {b_label}")
        embed.add_field(name=f"Round {round_number}", value="\n".join(lines) or "—", inline=False)
    return embed
