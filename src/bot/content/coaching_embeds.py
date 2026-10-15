"""Embeds for /coach (docs/DECISIONS.md ADR-126). Pure builders: no Discord
state and no database, so they're testable on their own.

Inside Discord a coach is named by mention. The website names them by their
linked Brawlhalla account only (ADR-040).
"""

from __future__ import annotations

from collections.abc import Sequence

import discord

from bot.palette import CREAM, EMERALD, GOLD, GREY
from database.models.coaching import Coach, CoachingRequest
from services.coaching_service import REQUEST_LIFETIME, CoachEntry, parse_legends
from services.legend_art import legend_display_name

FOOTER = "BRAWLISTAN Coaching"
_LIST_LIMIT = 15


def coaches_url(site_url: str) -> str:
    return f"{site_url.rstrip('/')}/coaches.html"


def coaches_view(site_url: str) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Coaches page", url=coaches_url(site_url), emoji="🎓"))
    return view


def _legends_text(raw: str | None) -> str | None:
    keys = parse_legends(raw)
    return ", ".join(legend_display_name(k) for k in keys) if keys else None


def _coach_line(entry: CoachEntry) -> str:
    coach = entry.coach
    parts = [f"<@{coach.discord_id}>"]
    if entry.player is not None:
        parts.append(f"({entry.player.player_name})")
    if entry.snapshot is not None and entry.snapshot.rating is not None:
        parts.append(f"· {entry.snapshot.rating}")
    status = "🟢" if coach.accepting else "⏸️"
    line = f"{status} " + " ".join(parts)
    details = [d for d in (coach.specialty, _legends_text(coach.legends), coach.availability) if d]
    if details:
        line += "\n-# " + " · ".join(details)
    return line


def build_coach_list_embed(entries: Sequence[CoachEntry], *, site_url: str) -> discord.Embed:
    embed = discord.Embed(title="🎓 Coaches", url=coaches_url(site_url), colour=GOLD)
    if not entries:
        embed.description = "No coaches yet. Staff give the Coach role to add one."
    else:
        shown = "\n".join(_coach_line(e) for e in entries[:_LIST_LIMIT])
        more = len(entries) - _LIST_LIMIT
        embed.description = shown + (f"\n…and {more} more on the website." if more > 0 else "")
    embed.set_footer(text="🟢 taking students · ⏸️ full · ask with /coach request")
    return embed


def build_request_card(
    request: CoachingRequest, coach: Coach, *, actor_id: int | None = None
) -> discord.Embed:
    """The card in the coaching channel; it changes as the coach answers."""
    status = request.status
    colour = {"open": CREAM, "accepted": EMERALD}.get(status, GREY)
    embed = discord.Embed(
        title=f"🎓 Coaching request #{request.id}",
        description=request.message,
        colour=colour,
    )
    embed.add_field(name="Student", value=f"<@{request.student_discord_id}>", inline=True)
    embed.add_field(name="Coach", value=f"<@{coach.discord_id}>", inline=True)
    label = {
        "open": "Waiting for the coach",
        "accepted": "✅ Accepted",
        "declined": "Declined",
    }.get(status, status.title())
    if actor_id is not None and actor_id != coach.discord_id and status != "open":
        label += f" by <@{actor_id}>"
    embed.add_field(name="Status", value=label, inline=True)
    days = REQUEST_LIFETIME.days
    embed.set_footer(text=f"{FOOTER} · open requests lapse after {days} days")
    return embed


def build_open_requests_embed(requests: Sequence[CoachingRequest]) -> discord.Embed:
    embed = discord.Embed(title="📥 Your open coaching requests", colour=CREAM)
    if not requests:
        embed.description = "Nothing waiting. New requests appear in the coaching channel."
        return embed
    embed.description = "\n".join(
        f"**#{r.id}** <@{r.student_discord_id}>: {r.message[:120]}" for r in requests
    )
    embed.set_footer(text="Answer with the buttons on each request card")
    return embed


def build_coach_profile_embed(coach: Coach) -> discord.Embed:
    embed = discord.Embed(title="🎓 Your coach profile", colour=GOLD)
    embed.add_field(name="Specialty", value=coach.specialty or "—", inline=True)
    embed.add_field(name="Legends", value=_legends_text(coach.legends) or "—", inline=True)
    embed.add_field(name="Availability", value=coach.availability or "—", inline=True)
    embed.add_field(name="Bio", value=coach.bio or "—", inline=False)
    embed.add_field(
        name="Taking students", value="Yes" if coach.accepting else "No (paused)", inline=True
    )
    if coach.brawlhalla_player_id is None:
        embed.add_field(
            name="Website",
            value="Not listed yet: link your Brawlhalla account with `/link` to appear there.",
            inline=False,
        )
    return embed
