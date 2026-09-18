"""/help — command discovery (docs/DECISIONS.md ADR-087).

Thin even by this project's standards: the catalog and all rendering live
in bot/content/help_embeds.py. No permission check and no database access —
/help is the one command that has to work for someone who has done nothing
else yet.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import ShaheenBot
from bot.content.help_embeds import HELP_SECTIONS, build_help_embed


class HelpCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Show what Shaheen Bot can do")
    @app_commands.describe(category="Show just one group of commands")
    @app_commands.choices(
        category=[
            app_commands.Choice(name=section.title, value=section.key) for section in HELP_SECTIONS
        ]
    )
    async def help(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
    ) -> None:
        # Ephemeral like every other read-only command here: /help in a busy
        # channel shouldn't push the conversation off-screen for everyone.
        await interaction.response.send_message(
            embed=build_help_embed(category.value if category else None), ephemeral=True
        )


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(HelpCog(bot))
