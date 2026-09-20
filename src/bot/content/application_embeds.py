"""Branded embeds for the join-application flow (docs/DECISIONS.md ADR-089)."""

from __future__ import annotations

import discord

from bot.palette import EMERALD, FOREST_GREEN, GOLD, GREY
from database.models.application import Application, ApplicationStatus

# Discord caps an embed field at 1024 characters; applicants write free text
# into a 1000-char paragraph box, so long answers are cut rather than
# risking a rejected embed that would lose the application card entirely.
_FIELD_LIMIT = 1000

_STATUS_COLOUR = {
    ApplicationStatus.PENDING: GOLD,
    ApplicationStatus.APPROVED: FOREST_GREEN,
    ApplicationStatus.DENIED: GREY,
    ApplicationStatus.WITHDRAWN: GREY,
}

_STATUS_LABEL = {
    ApplicationStatus.PENDING: "⏳ Under review",
    ApplicationStatus.APPROVED: "✅ Approved",
    ApplicationStatus.DENIED: "❌ Declined",
    ApplicationStatus.WITHDRAWN: "↩️ Withdrawn",
}


def _clip(value: object) -> str:
    text = str(value or "—").strip() or "—"
    return text if len(text) <= _FIELD_LIMIT else text[: _FIELD_LIMIT - 1] + "…"


def build_application_panel_embed() -> discord.Embed:
    """The permanent panel in #apply that the Apply button hangs off."""
    embed = discord.Embed(
        title="🦅 Apply to Shaheen",
        description=(
            "Shaheen is Pakistan's competitive Brawlhalla clan. Every application "
            "is read by staff — tell us who you are and why you want in.\n\n"
            "You'll need your **Brawlhalla ID or Steam64 ID** ready. "
            "Applying takes about a minute, and you'll hear back by DM."
        ),
        colour=GOLD,
    )
    embed.add_field(
        name="What we look for",
        value=(
            "• You play ranked and want to get better\n"
            "• You show up for scrims and tournaments\n"
            "• No toxicity, no smurfing, no excuses"
        ),
        inline=False,
    )
    embed.set_footer(text="One application at a time. Declined? You can reapply in 14 days.")
    return embed


def build_application_review_embed(
    application: Application, *, applicant: discord.abc.User | None = None
) -> discord.Embed:
    """The staff card in #applications.

    Everything below the header is the applicant's own words — untrusted
    input, clipped to fit and rendered as plain text.
    """
    answers = application.answers or {}
    status = application.status
    embed = discord.Embed(
        title=f"{_STATUS_LABEL[status]} — Application #{application.id}",
        colour=_STATUS_COLOUR[status],
    )
    if applicant is not None:
        embed.set_author(name=str(applicant), icon_url=applicant.display_avatar.url)
        embed.description = f"{applicant.mention} · `{applicant.id}`"
    else:
        # The applicant may have left the server between applying and review.
        embed.description = f"<@{application.discord_id}> · `{application.discord_id}`"

    embed.add_field(
        name="Brawlhalla / Steam ID",
        value=f"`{_clip(application.brawlhalla_identifier)}`",
        inline=True,
    )
    embed.add_field(name="Region", value=_clip(answers.get("region")), inline=True)
    embed.add_field(name="Current Rank", value=_clip(answers.get("current_rank")), inline=True)
    embed.add_field(name="Why Shaheen", value=_clip(answers.get("motivation")), inline=False)
    if answers.get("referred_by"):
        embed.add_field(name="Referred by", value=_clip(answers.get("referred_by")), inline=True)

    if application.attempt > 1:
        embed.add_field(
            name="Attempt", value=f"#{application.attempt} for this member", inline=True
        )

    if status is not ApplicationStatus.PENDING and application.reviewer_discord_id:
        detail = f"<@{application.reviewer_discord_id}>"
        if application.review_note:
            detail += f" — {_clip(application.review_note)}"
        embed.add_field(name="Reviewed by", value=detail, inline=False)

    embed.set_footer(text=f"Submitted · applicant {application.discord_id}")
    if application.created_at is not None:
        embed.timestamp = application.created_at
    return embed


def build_application_submitted_embed(application: Application) -> discord.Embed:
    return discord.Embed(
        title="✅ Application submitted",
        description=(
            f"Your application (**#{application.id}**) is with staff now. "
            "You'll get a DM once it's been reviewed — make sure your DMs are open."
        ),
        colour=FOREST_GREEN,
    )


def build_application_status_embed(application: Application | None) -> discord.Embed:
    if application is None:
        return discord.Embed(
            title="No application yet",
            description="Use `/apply` — or the button in #📝-apply — to get started.",
            colour=GREY,
        )
    embed = discord.Embed(
        title=f"Application #{application.id}",
        description=_STATUS_LABEL[application.status],
        colour=_STATUS_COLOUR[application.status],
    )
    if application.review_note:
        embed.add_field(name="Staff note", value=_clip(application.review_note), inline=False)
    return embed


def build_application_decision_dm_embed(
    application: Application, *, guild_name: str
) -> discord.Embed:
    """What the applicant is told. A denial stays short and non-personal."""
    if application.status is ApplicationStatus.APPROVED:
        embed = discord.Embed(
            title=f"🦅 Welcome to {guild_name}",
            description=(
                "Your application was approved. Head back to the server, run `/link` "
                "to connect your Brawlhalla account, and say hello in the chat."
            ),
            colour=FOREST_GREEN,
        )
    else:
        embed = discord.Embed(
            title="Application declined",
            description=(
                f"Thanks for applying to {guild_name}. This one wasn't a fit — "
                "you're welcome to apply again in 14 days."
            ),
            colour=GREY,
        )
    if application.review_note:
        embed.add_field(name="From the staff", value=_clip(application.review_note), inline=False)
    return embed


def build_pending_queue_embed(
    entries: list[tuple[Application, str]], *, guild_name: str
) -> discord.Embed:
    """entries: (application, resolved display name) — oldest first."""
    embed = discord.Embed(title=f"📥 {guild_name} — Pending Applications", colour=EMERALD)
    if not entries:
        embed.description = "Nothing waiting. The queue is clear."
        return embed

    embed.description = "\n".join(
        f"**#{application.id}** — {name} · {_clip(application.answers.get('current_rank'))}"
        + (f" · attempt #{application.attempt}" if application.attempt > 1 else "")
        for application, name in entries
    )
    embed.set_footer(text=f"{len(entries)} waiting · review them in #📥-applications")
    return embed
