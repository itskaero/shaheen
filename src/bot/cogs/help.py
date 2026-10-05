"""/help — command discovery (docs/DECISIONS.md ADR-087).

Thin even by this project's standards: the catalog and all rendering live
in bot/content/help_embeds.py, the pagination in bot/views/help.py
(ADR-121). No permission check and no database access —
/help is the one command that has to work for someone who has done nothing
else yet.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import check_staff_authorized
from bot.client import ShaheenBot
from bot.content.help_embeds import HELP_SECTIONS, help_pages
from bot.views.help import HelpPaginator


class HelpCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Show what the BRAWLISTAN bot can do")
    @app_commands.describe(category="Open on one group of commands")
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
        # Paginated (ADR-121): one category per page, staff pages for staff only.
        member = interaction.user
        staff = isinstance(member, discord.Member) and check_staff_authorized(
            member, self.bot.settings.bot_owner_id
        )
        pages = help_pages(staff=staff)
        start = next(
            (
                i
                for i, page in enumerate(pages)
                if page is not None and category and page.key == category.value
            ),
            0,
        )
        view = HelpPaginator(pages, author_id=member.id, start=start)
        # Ephemeral like every other read-only command: /help in a busy
        # channel shouldn't push the conversation off-screen for everyone.
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)
        view.message = await interaction.original_response()


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(HelpCog(bot))
