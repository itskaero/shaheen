"""/emoji sync and /emoji browse — Shaheen's legend-expression emoji.

Thin (docs/ARCHITECTURE.md): the upload logic lives in
services/emoji_service.py, the copy in bot/content/emoji_embeds.py, the
picker's interactive state in bot/views/emoji_picker.py
(docs/DECISIONS.md ADR-090/ADR-092).
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import require_staff_authorized
from bot.client import ShaheenBot
from bot.content.emoji_embeds import build_emoji_sync_embed
from bot.views.emoji_picker import EmojiBrowseView
from core.exceptions import ShaheenError
from services.emoji_service import EmojiService


class EmojiCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    emoji_group = app_commands.Group(name="emoji", description="Manage Shaheen's server emoji pack")

    @emoji_group.command(
        name="sync", description="Upload Shaheen's legend emoji pack to this server (staff only)"
    )
    @require_staff_authorized()
    async def sync(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        report = await EmojiService(interaction.guild).sync()
        await interaction.followup.send(embed=build_emoji_sync_embed(report), ephemeral=True)

    @emoji_group.command(
        name="browse",
        description="Browse candidate legend emoji and pick which to upload (staff only)",
    )
    @require_staff_authorized()
    async def browse(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")

        view = EmojiBrowseView(author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=view.current_embed(), view=view, ephemeral=True
        )


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(EmojiCog(bot))
