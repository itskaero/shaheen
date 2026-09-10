"""Shared base for persistent (restart-surviving) views.

Unlike the session-lived views in bot/views/competition.py (bounded
timeout, no custom_id routing — docs/DECISIONS.md ADR-038), a
PersistentView uses timeout=None and its items carry static custom_ids, so
discord.py can route an interaction back to it even after a bot restart —
but only once ShaheenBot.setup_hook() re-registers an instance via
self.add_view() on every process start (docs/DECISIONS.md ADR-058).
"""

from __future__ import annotations

import logging

import discord

from core.exceptions import ShaheenError

logger = logging.getLogger(__name__)


class PersistentView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ) -> None:
        """Mirrors ShaheenBot._on_app_command_error — a persistent view's
        button callbacks aren't routed through the app-command error
        handler, so they need the same ShaheenError-vs-unexpected split.
        """
        if isinstance(error, ShaheenError):
            message = f"⚠️ {error}"
        else:
            logger.exception(
                "Unhandled error in persistent view %s", type(self).__name__, exc_info=error
            )
            message = "⚠️ Something went wrong on Shaheen's side. This has been logged."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
