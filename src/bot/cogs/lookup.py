"""/lookup — check any Brawlhalla player's standing without linking.

Read-only and ephemeral: nothing is written to the database and no link is
created (docs/DECISIONS.md ADR-083). Usable by any member, matching the
no-permission-check posture of /profile.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import ShaheenBot
from bot.content.lookup_embeds import build_lookup_embed, build_lookup_help_embed
from core.exceptions import NotFoundError, ShaheenError
from database.session import session_scope
from services.lookup_service import LookupService


class LookupCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="lookup", description="Check any Brawlhalla player's rank against the clan"
    )
    @app_commands.describe(identifier="A Steam64 ID (17 digits) or a Brawlhalla player ID")
    async def lookup(self, interaction: discord.Interaction, identifier: str) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            service = LookupService(session, self.bot.brawlhalla)
            try:
                result = await service.lookup(guild_id=interaction.guild.id, identifier=identifier)
            except NotFoundError as exc:
                # Not a generic error: Brawlhalla has no name search, so the
                # usual cause is someone typing a username. The help embed
                # says what's accepted and where to find it, instead of the
                # bare "⚠️ ..." the global handler would show.
                await interaction.followup.send(
                    embed=build_lookup_help_embed(str(exc)), ephemeral=True
                )
                return

        await interaction.followup.send(embed=build_lookup_embed(result), ephemeral=True)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(LookupCog(bot))
