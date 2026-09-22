"""/emoji sync, /emoji browse, and /emoji clear — Shaheen's legend-
expression emoji.

Thin (docs/ARCHITECTURE.md): the upload/delete logic lives in
services/emoji_service.py, the copy in bot/content/emoji_embeds.py, the
picker's interactive state in bot/views/emoji_picker.py
(docs/DECISIONS.md ADR-090/ADR-092/ADR-094).
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import require_setup_authorized, require_staff_authorized
from bot.client import ShaheenBot
from bot.content.emoji_embeds import (
    build_emoji_clear_report_embed,
    build_emoji_clear_warning_embed,
    build_emoji_sync_embed,
)
from bot.views.emoji_picker import EmojiBrowseView
from core.exceptions import ShaheenError
from services.emoji_service import EmojiService

_CLEAR_CONFIRM_TEXT = "DELETE ALL EMOJI"


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

    @emoji_group.command(
        name="clear",
        description="DESTRUCTIVE: delete every custom emoji in this server (admin only)",
    )
    @require_setup_authorized()
    async def clear(self, interaction: discord.Interaction) -> None:
        """Deletes every custom emoji in the guild, regardless of origin —
        far more destructive than sync/browse, so it gets /setup reset's
        two-step warning-then-typed-confirm pattern (docs/DECISIONS.md
        ADR-060/ADR-094) and the tighter admin-only gate instead of
        sync/browse's staff gate.
        """
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")

        view = _EmojiClearWarningView(author_id=interaction.user.id, guild=interaction.guild)
        await interaction.response.send_message(
            embed=build_emoji_clear_warning_embed(), view=view, ephemeral=True
        )


class _EmojiClearWarningView(discord.ui.View):
    """Step 1: a plain button — send_modal must be the direct response to
    the triggering interaction, so the modal (step 2) is where the "type
    to confirm" check happens (same shape as setup.py's _ResetWarningView).
    """

    def __init__(self, *, author_id: int, guild: discord.Guild) -> None:
        super().__init__(timeout=120)
        self._author_id = author_id
        self._guild = guild

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._author_id:
            await interaction.response.send_message(
                "Only the person who ran this command can respond.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Continue to confirm", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def continue_(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.send_modal(_EmojiClearConfirmModal(self._guild))
        self.stop()


class _EmojiClearConfirmModal(discord.ui.Modal, title="Confirm Emoji Clear"):
    confirmation: discord.ui.TextInput = discord.ui.TextInput(
        label=f'Type "{_CLEAR_CONFIRM_TEXT}" to confirm',
        placeholder=_CLEAR_CONFIRM_TEXT,
        max_length=32,
    )

    def __init__(self, guild: discord.Guild) -> None:
        super().__init__()
        self._guild = guild

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.confirmation.value.strip() != _CLEAR_CONFIRM_TEXT:
            await interaction.response.send_message(
                f"Clear cancelled — you must type `{_CLEAR_CONFIRM_TEXT}` exactly.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        report = await EmojiService(self._guild).clear()
        await interaction.followup.send(
            embed=build_emoji_clear_report_embed(report), ephemeral=True
        )


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(EmojiCog(bot))
