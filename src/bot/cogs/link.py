"""/link and /unlink.

Stays thin (docs/ARCHITECTURE.md): all persistence/Brawlhalla orchestration
lives in services/link_service.py; this cog only handles the Discord-side
flow (confirmation, role promotion) described in docs/COMMANDS.md.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import ShaheenBot
from bot.constants import ROLE_GUEST, ROLE_TRIAL, ROLES
from bot.content.profile_embeds import (
    build_link_preview_embed,
    build_link_success_embed,
    build_unlink_confirm_embed,
    build_unlink_success_embed,
)
from bot.views.confirm import ConfirmView
from core.exceptions import ShaheenError
from database.session import session_scope
from services.link_service import LinkService

logger = logging.getLogger(__name__)


class LinkCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="link", description="Link your Discord account to a Brawlhalla player"
    )
    @app_commands.describe(identifier="Your Brawlhalla player ID or Steam64 ID")
    async def link(self, interaction: discord.Interaction, identifier: str) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This command can only be used inside the Shaheen server.")

        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            candidate = await link_service.resolve_candidate(identifier)
            existing = await link_service.get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )
        previous_name = existing[1].player_name if existing else None

        preview = build_link_preview_embed(
            candidate_name=candidate.name,
            candidate_id=candidate.brawlhalla_id,
            previous_player_name=previous_name,
        )
        view = ConfirmView(author_id=member.id)
        message = await interaction.followup.send(
            embed=preview, view=view, ephemeral=True, wait=True
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Link cancelled.", embed=None, view=None)
            return

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            outcome = await link_service.link(
                guild_id=member.guild.id,
                discord_id=member.id,
                joined_at=member.joined_at,
                candidate=candidate,
            )

        promoted = await self._maybe_promote(member)
        embed = build_link_success_embed(player_name=outcome.player.player_name, promoted=promoted)
        await message.edit(content=None, embed=embed, view=None)

    @app_commands.command(name="unlink", description="Remove your active Brawlhalla link")
    async def unlink(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This command can only be used inside the Shaheen server.")

        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            existing = await link_service.get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )

        if existing is None:
            await interaction.followup.send(
                "You don't have an active Brawlhalla link.", ephemeral=True
            )
            return

        player_name = existing[1].player_name
        view = ConfirmView(author_id=member.id)
        message = await interaction.followup.send(
            embed=build_unlink_confirm_embed(player_name), view=view, ephemeral=True, wait=True
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Unlink cancelled.", embed=None, view=None)
            return

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            await link_service.unlink(guild_id=member.guild.id, discord_id=member.id)

        await message.edit(content=None, embed=build_unlink_success_embed(player_name), view=None)

    async def _maybe_promote(self, member: discord.Member) -> bool:
        """Promote GUEST -> TRIAL SHAHEEN on link (docs/DECISIONS.md ADR-026).

        Members who already hold Trial or any higher rank role are left
        unchanged — promotion beyond Trial stays a manual staff decision.
        """
        rank_role_names = {
            role.name for role in ROLES if role.logical_key != ROLE_GUEST.logical_key
        }
        member_role_names = {role.name for role in member.roles}
        if member_role_names & rank_role_names:
            return False

        guild = member.guild
        guest_role = discord.utils.get(guild.roles, name=ROLE_GUEST.name)
        trial_role = discord.utils.get(guild.roles, name=ROLE_TRIAL.name)
        if trial_role is None:
            return False  # /setup hasn't run yet; nothing to assign.

        try:
            if guest_role is not None and guest_role in member.roles:
                await member.remove_roles(guest_role, reason="Shaheen /link")
            await member.add_roles(trial_role, reason="Shaheen /link")
        except discord.Forbidden:
            logger.warning("Missing permission to promote %s after /link", member.id)
            return False
        return True


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(LinkCog(bot))
