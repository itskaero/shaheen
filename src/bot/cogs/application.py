"""/apply, /application, /applications — the join-approval flow.

Thin (docs/ARCHITECTURE.md): the rules live in
services/application_service.py, the Discord surfaces in
bot/views/application.py, and the copy in
bot/content/application_embeds.py (docs/DECISIONS.md ADR-089).
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import require_staff_authorized
from bot.client import ShaheenBot
from bot.content.application_embeds import (
    build_application_status_embed,
    build_pending_queue_embed,
)
from bot.membership import is_already_a_clan_member
from bot.views.application import ApplicationModal
from core.exceptions import ShaheenError
from database.session import session_scope
from services.application_service import ApplicationService


class ApplicationCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(name="apply", description="Apply to join the Shaheen clan roster")
    async def apply(self, interaction: discord.Interaction) -> None:
        """The same form the #📝-apply panel opens.

        Both exist because a panel is discoverable and a command is
        findable: someone who has scrolled past the channel can still type
        /apply. Distinct from /verify (bot/cogs/moderation.py): this is a
        roster application, not general server access — docs/DECISIONS.md
        ADR-092.
        """
        member = interaction.user
        if not isinstance(member, discord.Member) or interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        if is_already_a_clan_member(member):
            raise ShaheenError("You're already on the roster — no application needed.")
        await interaction.response.send_modal(ApplicationModal())

    @app_commands.command(
        name="application", description="Check the status of your Shaheen application"
    )
    async def application(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            latest = await ApplicationService(session).latest_for(
                guild_id=interaction.guild.id, discord_id=interaction.user.id
            )
            embed = build_application_status_embed(latest)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="applications", description="List applications awaiting review (staff only)"
    )
    @require_staff_authorized()
    async def applications(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        async with session_scope(self.bot.session_factory) as session:
            pending = await ApplicationService(session).pending(guild.id)
            entries = []
            for application in pending:
                member = guild.get_member(application.discord_id)
                # The applicant may have left; the queue still shows the row
                # so staff can close it out rather than leaving it stuck.
                name = member.display_name if member else f"<@{application.discord_id}> (left)"
                entries.append((application, name))
            embed = build_pending_queue_embed(entries, guild_name=guild.name)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(ApplicationCog(bot))
