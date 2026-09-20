"""The apply panel, the application form, and the staff review card.

docs/DECISIONS.md ADR-089. Three persistent pieces:

- ApplicationPanelView — the permanent "Apply to Shaheen" button in
  #📝-apply, posted once by /setup the same way the self-assign role panel
  is (bot/views/roles.py).
- ApplicationModal — the form itself. Discord allows at most five inputs,
  which is exactly the five questions that decide an application.
- ApplicationReviewView — Approve / Deny on every card in #📥-applications.

The review buttons carry **static** custom_ids and find their application by
`interaction.message.id` against `Application.review_message_id`. The
alternative — baking the application id into each custom_id — needs
discord.py's DynamicItem and a regex template; looking it up from the
message the button is already attached to reuses a column we store anyway
and keeps one registered view serving every card, forever, across restarts.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, cast

import discord

from bot.checks.permissions import check_staff_authorized
from bot.content.application_embeds import (
    build_application_decision_dm_embed,
    build_application_review_embed,
    build_application_submitted_embed,
)
from bot.membership import grant_member_access, is_already_verified
from bot.views.base import PersistentView
from core.exceptions import PermissionDeniedError, ShaheenError
from database.models.application import Application
from database.session import session_scope
from services.application_service import ApplicationAnswers, ApplicationService

if TYPE_CHECKING:
    from bot.client import ShaheenBot

logger = logging.getLogger(__name__)

APPLICATIONS_CHANNEL_KEY = "channel:applications"
APPLY_CHANNEL_KEY = "channel:apply"


class ApplicationPanelView(PersistentView):
    """The permanent panel in #📝-apply."""

    def __init__(self) -> None:
        super().__init__()

    @discord.ui.button(
        label="Apply to Shaheen",
        emoji="🦅",
        style=discord.ButtonStyle.success,
        custom_id="shaheen:application:apply",
    )
    async def apply(
        self, interaction: discord.Interaction, _button: discord.ui.Button[ApplicationPanelView]
    ) -> None:
        await interaction.response.send_modal(ApplicationModal())


class ApplicationModal(discord.ui.Modal, title="Apply to Shaheen"):
    identifier: discord.ui.TextInput[ApplicationModal] = discord.ui.TextInput(
        label="Brawlhalla ID or Steam64 ID",
        placeholder="e.g. 76561198000000000",
        max_length=32,
        required=True,
    )
    region: discord.ui.TextInput[ApplicationModal] = discord.ui.TextInput(
        label="Region / timezone",
        placeholder="e.g. Pakistan (PKT), SEA servers",
        max_length=64,
        required=True,
    )
    current_rank: discord.ui.TextInput[ApplicationModal] = discord.ui.TextInput(
        label="Current ranked tier",
        placeholder="e.g. Platinum 2, or Unranked",
        max_length=32,
        required=True,
    )
    motivation: discord.ui.TextInput[ApplicationModal] = discord.ui.TextInput(
        label="Why Shaheen?",
        style=discord.TextStyle.paragraph,
        placeholder="How often you play, what you want out of the clan, what you bring.",
        max_length=1000,
        required=True,
    )
    referred_by: discord.ui.TextInput[ApplicationModal] = discord.ui.TextInput(
        label="Referred by (optional)",
        placeholder="A member who told you about us",
        max_length=64,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or interaction.guild is None:
            raise ShaheenError("Applications can only be submitted inside the Shaheen server.")
        if is_already_verified(member):
            raise ShaheenError("You're already a member here — no application needed.")

        await interaction.response.defer(ephemeral=True)
        bot = cast("ShaheenBot", interaction.client)
        guild = interaction.guild

        async with session_scope(bot.session_factory) as session:
            service = ApplicationService(session)
            application = await service.submit(
                guild_id=guild.id,
                discord_id=member.id,
                answers=ApplicationAnswers(
                    brawlhalla_identifier=self.identifier.value.strip(),
                    region=self.region.value.strip(),
                    current_rank=self.current_rank.value.strip(),
                    motivation=self.motivation.value.strip(),
                    referred_by=(self.referred_by.value or "").strip() or None,
                ),
            )
            # Post the review card inside the same transaction so the stored
            # message id and the row are written together — a card with no
            # row would have dead buttons.
            message = await _post_review_card(bot, guild, application, applicant=member)
            if message is not None:
                await service.attach_review_message(application, message.id)

            embed = build_application_submitted_embed(application)

        await interaction.followup.send(embed=embed, ephemeral=True)


class ApplicationReviewView(PersistentView):
    """Approve / Deny, attached to every card in #📥-applications."""

    @discord.ui.button(
        label="Approve",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="shaheen:application:approve",
    )
    async def approve(
        self, interaction: discord.Interaction, _button: discord.ui.Button[ApplicationReviewView]
    ) -> None:
        await _decide(interaction, approved=True, note=None)

    @discord.ui.button(
        label="Decline",
        emoji="✖️",
        style=discord.ButtonStyle.secondary,
        custom_id="shaheen:application:deny",
    )
    async def deny(
        self, interaction: discord.Interaction, _button: discord.ui.Button[ApplicationReviewView]
    ) -> None:
        _require_staff(interaction)
        await interaction.response.send_modal(DenyReasonModal())


class DenyReasonModal(discord.ui.Modal, title="Decline application"):
    note: discord.ui.TextInput[DenyReasonModal] = discord.ui.TextInput(
        label="Reason (shared with the applicant)",
        style=discord.TextStyle.paragraph,
        placeholder="Optional. Kept short and factual.",
        max_length=400,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await _decide(interaction, approved=False, note=(self.note.value or "").strip() or None)


def _require_staff(interaction: discord.Interaction) -> discord.Member:
    reviewer = interaction.user
    if not isinstance(reviewer, discord.Member):
        raise PermissionDeniedError("Applications can only be reviewed inside the server.")
    if not check_staff_authorized(reviewer):
        raise PermissionDeniedError("Only staff can review applications.")
    return reviewer


async def _decide(interaction: discord.Interaction, *, approved: bool, note: str | None) -> None:
    reviewer = _require_staff(interaction)
    if interaction.message is None or interaction.guild is None:
        raise ShaheenError("That application card can no longer be read.")

    await interaction.response.defer(ephemeral=True)
    bot = cast("ShaheenBot", interaction.client)
    guild = interaction.guild
    message = interaction.message

    async with session_scope(bot.session_factory) as session:
        service = ApplicationService(session)
        application = await service.for_review_message(message.id)
        if application is None:
            raise ShaheenError(
                "No application is attached to this card — it may predate the application system."
            )
        # Raises if it was already decided; the guard is what makes a stale
        # card or a double click safe.
        await service.decide(
            application, approved=approved, reviewer_discord_id=reviewer.id, note=note
        )
        applicant = guild.get_member(application.discord_id)
        decided_embed = build_application_review_embed(application, applicant=applicant)
        dm_embed = build_application_decision_dm_embed(application, guild_name=guild.name)

    if approved and applicant is not None:
        await grant_member_access(
            applicant, reason=f"Shaheen application #{application.id} approved by {reviewer}"
        )

    # Retire the card's buttons so a settled application can't be clicked again.
    with contextlib.suppress(discord.HTTPException):
        await message.edit(embed=decided_embed, view=None)

    if applicant is not None:
        with contextlib.suppress(discord.Forbidden, discord.HTTPException):
            # Best-effort: closed DMs must not fail the decision.
            await applicant.send(embed=dm_embed)

    verb = "approved" if approved else "declined"
    await interaction.followup.send(
        f"✅ Application #{application.id} {verb}."
        + ("" if applicant is not None else " (The applicant has left the server.)"),
        ephemeral=True,
    )


async def _post_review_card(
    bot: ShaheenBot,
    guild: discord.Guild,
    application: Application,
    *,
    applicant: discord.Member,
) -> discord.Message | None:
    """Post the card to #📥-applications. Returns None if it can't be posted.

    A missing channel or permission must not lose the application: the row
    is already written and `/applications` still lists it.
    """
    # Imported here to avoid a circular import at module load — cogs import
    # views, and this needs the cog module's channel resolver.
    from bot.cogs.competition import resolve_provisioned_channel

    channel = await resolve_provisioned_channel(bot, guild, APPLICATIONS_CHANNEL_KEY)
    if channel is None:
        logger.warning("Applications channel not provisioned — run /setup run")
        return None
    try:
        return await channel.send(
            embed=build_application_review_embed(application, applicant=applicant),
            view=ApplicationReviewView(),
        )
    except discord.Forbidden:
        logger.warning("Missing permission to post in the applications channel")
        return None
