"""Branded embeds for /challenge, /scrim, /match, /report, /matches, /tournament."""

from __future__ import annotations

import discord

from bot.palette import EMERALD, FOREST_GREEN, GOLD, GREY
from database.models.match import Match, MatchKind, MatchStatus
from database.models.tournament import Tournament, TournamentMatch, TournamentMatchStatus


def build_spar_kiosk_embed() -> discord.Embed:
    """Posted with SparKioskView attached (bot/cogs/setup.py, docs/DECISIONS.md
    ADR-058) — clicking either button runs the same flow as /scrim.
    """
    return discord.Embed(
        title="🥊 Looking to Spar?",
        description=(
            "Click below to announce a scrim — Shaheen posts it in #scrims "
            "with a Join button for whoever's up.\n\n"
            "Prefer picking a specific mode or teammate? Use `/scrim` or `/challenge` instead."
        ),
        colour=GOLD,
    )


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
                f"**{opponent_name}** accepted. Good luck — report the result with `/report`."
            ),
            colour=FOREST_GREEN,
        )
    return discord.Embed(
        title="Challenge Declined",
        description=f"**{opponent_name}** declined the challenge.",
        colour=GREY,
    )


def build_scrim_embed(
    *, creator_name: str, kind: MatchKind, side_counts: tuple[int, int]
) -> discord.Embed:
    capacity = 1 if kind is MatchKind.ONE_V_ONE else 2
    a_count, b_count = side_counts
    embed = discord.Embed(
        title=f"⚔️ Scrim — {kind.value}",
        description=f"Organized by **{creator_name}**. Join below!",
        colour=GOLD,
    )
    embed.add_field(name="Side A", value=f"{a_count}/{capacity}", inline=True)
    embed.add_field(name="Side B", value=f"{b_count}/{capacity}", inline=True)
    return embed


def build_scrim_full_embed(*, kind: MatchKind) -> discord.Embed:
    return discord.Embed(
        title="✅ Scrim Full",
        description=(
            f"The {kind.value} scrim is full — good luck! Report the result with `/report`."
        ),
        colour=FOREST_GREEN,
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
        description="A Moderator or Leader will need to resolve this with `/match resolve`.",
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
