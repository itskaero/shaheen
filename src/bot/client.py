"""The Shaheen Discord client.

Cogs stay thin (docs/ARCHITECTURE.md): this module wires intents, command
sync, and a single error boundary that keeps raw exceptions away from users
(docs/COMMANDS.md), and hands each cog whatever services/repositories it
needs via dependency attributes on the bot instance rather than a framework.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.views.roles import SelfAssignRolesView
from bot.views.spar import SparKioskView
from core.config import Settings
from core.exceptions import ShaheenError
from integrations.brawlhalla.client import BrawlhallaClient
from integrations.brawlhalla.service import BrawlhallaService

logger = logging.getLogger(__name__)

# ADR-012: request every gateway intent, including the privileged ones
# (members, presences, message_content). These must also be enabled for the
# application in the Discord Developer Portal.
INTENTS = discord.Intents.all()

STARTUP_EXTENSIONS = (
    "bot.cogs.setup",
    "bot.cogs.link",
    "bot.cogs.profile",
    "bot.cogs.clan",
    "bot.cogs.competition",
    "bot.cogs.moderation",
    "bot.cogs.engagement",
)


class ShaheenBot(commands.Bot):
    def __init__(
        self, *, settings: Settings, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        super().__init__(command_prefix=commands.when_mentioned, intents=INTENTS)
        self.settings = settings
        self.session_factory = session_factory
        self.brawlhalla = BrawlhallaService(
            BrawlhallaClient(settings.brawlhalla_api_key.get_secret_value())
        )
        # discord.py's documented way to override the tree's default error handler.
        self.tree.on_error = self._on_app_command_error  # type: ignore[method-assign]

    async def setup_hook(self) -> None:
        # Persistent views (docs/DECISIONS.md ADR-058) must be re-registered
        # on every process start — discord.py routes an interaction to
        # whichever registered view has a matching custom_id, regardless of
        # which message it's actually attached to, but only while a view
        # with that custom_id has been added here. Unlike the cogs below,
        # these aren't tied to any specific message and survive restarts.
        self.add_view(SelfAssignRolesView())
        self.add_view(SparKioskView())

        for extension in STARTUP_EXTENSIONS:
            await self.load_extension(extension)

        # ADR-013: guild-scoped sync only, for instant propagation on the
        # single guild Shaheen operates.
        guild = discord.Object(id=self.settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info(
            "Synced %d application command(s) to guild %s", len(synced), self.settings.guild_id
        )

    async def on_ready(self) -> None:
        logger.info("Shaheen Bot ready as %s (guild=%s)", self.user, self.settings.guild_id)

    async def close(self) -> None:
        await self.brawlhalla.aclose()
        await super().close()

    async def _on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        original = getattr(error, "original", error)

        if isinstance(original, ShaheenError):
            message = f"⚠️ {original}"
        elif isinstance(error, app_commands.CheckFailure):
            message = f"⚠️ {error}" if str(error) else "⚠️ You can't run this command."
        else:
            logger.exception("Unhandled application command error", exc_info=original)
            message = "⚠️ Something went wrong on Shaheen's side. This has been logged."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
