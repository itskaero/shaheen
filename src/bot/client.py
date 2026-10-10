"""The Shaheen Discord client.

Cogs stay thin (docs/ARCHITECTURE.md): this module wires intents, command
sync, and a single error boundary that keeps raw exceptions away from users
(docs/COMMANDS.md), and hands each cog whatever services/repositories it
needs via dependency attributes on the bot instance rather than a framework.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.constants import CHANNEL_REPORT
from bot.content.error_embeds import build_error_report_embed, error_reference
from bot.views.spar import SparKioskView
from core.config import Settings
from core.exceptions import ShaheenError
from database.models.provisioned_resource import ResourceType
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope
from integrations.brawlhalla.client import BrawlhallaClient
from integrations.brawlhalla.service import BrawlhallaService
from services.seasons import brawlhalla_season_at

logger = logging.getLogger(__name__)

# ADR-012: request every gateway intent, including the privileged ones
# (members, presences, message_content). These must also be enabled for the
# application in the Discord Developer Portal.
INTENTS = discord.Intents.all()

STARTUP_EXTENSIONS = (
    "bot.cogs.help",
    "bot.cogs.setup",
    "bot.cogs.link",
    "bot.cogs.profile",
    "bot.cogs.lookup",
    "bot.cogs.clan",
    "bot.cogs.pakistan",
    "bot.cogs.competition",
    "bot.cogs.moderation",
    "bot.cogs.engagement",
    "bot.cogs.emoji",
    "bot.cogs.network",
    "bot.cogs.staff",
    "bot.cogs.teams",
    "bot.cogs.access",
    "bot.cogs.coaching",
)


class ShaheenBot(commands.Bot):
    def __init__(
        self, *, settings: Settings, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        super().__init__(command_prefix=commands.when_mentioned, intents=INTENTS)
        self.settings = settings
        self.session_factory = session_factory
        self.brawlhalla = BrawlhallaService(
            BrawlhallaClient(
                settings.brawlhalla_api_key.get_secret_value(),
                base_url=settings.brawlhalla_api_base_url,
            )
        )
        # discord.py's documented way to override the tree's default error handler.
        self.tree.on_error = self._on_app_command_error  # type: ignore[method-assign]

    def current_brawlhalla_season(self) -> int:
        """The season every new snapshot is stamped with (ADR-088/ADR-102)."""
        return brawlhalla_season_at(datetime.now(UTC), override=self.settings.brawlhalla_season)

    async def setup_hook(self) -> None:
        # Persistent views (docs/DECISIONS.md ADR-058) must be re-registered
        # on every process start — discord.py routes an interaction to
        # whichever registered view has a matching custom_id, regardless of
        # which message it's actually attached to, but only while a view
        # with that custom_id has been added here. Unlike the cogs below,
        # these aren't tied to any specific message and survive restarts.
        # The spar kiosk in #looking-for-game. The self-assign roles panel
        # and the clan application views retired with ADR-109.
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
        logger.info("BRAWLISTAN bot ready as %s (guild=%s)", self.user, self.settings.guild_id)

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
            # A shared reference ties the member's message, the staff copy
            # and the traceback in the logs together (ADR-126).
            reference = error_reference()
            command = interaction.command.qualified_name if interaction.command else "unknown"
            logger.error(
                "Unhandled application command error [%s] in /%s",
                reference,
                command,
                exc_info=original,
            )
            message = (
                "⚠️ Something went wrong on BRAWLISTAN's side. Staff have been told "
                f"(ref `{reference}`)."
            )
            await self._report_error(interaction, command, reference, original)

        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            # The interaction expired or was deleted; the log has the error.
            logger.warning("Couldn't send the error message to the member", exc_info=True)

    async def _report_error(
        self,
        interaction: discord.Interaction,
        command: str,
        reference: str,
        error: BaseException,
    ) -> None:
        """Post a staff copy of an unexpected error to the mod-log channel.
        Best effort: never raises."""
        guild = interaction.guild
        if guild is None:
            return
        try:
            channel = await self._staff_channel(guild)
            if channel is None:
                return
            await channel.send(
                embed=build_error_report_embed(
                    command=command,
                    reference=reference,
                    error=error,
                    user_id=interaction.user.id if interaction.user else None,
                ),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception:
            logger.warning("Couldn't post the error report for %s", reference, exc_info=True)

    async def _staff_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """MOD_LOG_CHANNEL_ID, then REPORT_CHANNEL_ID, then the provisioned #report."""
        for channel_id in (self.settings.mod_log_channel_id, self.settings.report_channel_id):
            if channel_id is not None:
                channel = guild.get_channel(channel_id)
                if isinstance(channel, discord.TextChannel):
                    return channel
        async with session_scope(self.session_factory) as session:
            resource = await ProvisionedResourceRepository(session).get(
                guild_id=guild.id,
                resource_type=ResourceType.CHANNEL,
                logical_key=CHANNEL_REPORT.logical_key,
            )
        channel = guild.get_channel(resource.discord_id) if resource else None
        return channel if isinstance(channel, discord.TextChannel) else None
