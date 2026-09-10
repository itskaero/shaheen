"""/setup command group.

Stays thin (docs/ARCHITECTURE.md): permission/preflight checks and command
plumbing live here; all planning and execution logic lives in
services/setup_planner.py and services/setup_service.py.

docs/COMMANDS.md's bare `/setup` is exposed as `/setup run` — see
docs/DECISIONS.md ADR-016 for why Discord's slash command schema forces
that split.
"""

from __future__ import annotations

import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot.checks.permissions import require_setup_authorized
from bot.client import ShaheenBot
from bot.content.competition_embeds import build_spar_kiosk_embed
from bot.content.embeds import (
    build_plan_embed,
    build_report_embed,
    build_roles_embed,
    build_rules_embed,
    build_self_assign_roles_embed,
    build_status_embed,
    build_verify_embed,
    build_welcome_embed,
)
from bot.views.confirm import ConfirmView
from bot.views.roles import SelfAssignRolesView
from bot.views.spar import SparKioskView
from core.exceptions import SetupError
from database.models.provisioned_resource import ResourceType
from database.repositories.guild_settings_repository import GuildSettingsRepository
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope
from services.setup_service import SetupService

logger = logging.getLogger(__name__)

REQUIRED_BOT_PERMISSIONS = discord.Permissions(
    manage_roles=True, manage_channels=True, view_channel=True
)

# Channels that get one or more branded messages deployed in launch mode
# (see _deploy_launch_messages for what each one gets).
_LAUNCH_MESSAGE_CHANNELS: tuple[str, ...] = (
    "channel:welcome",
    "channel:rules",
    "channel:roles",
    "channel:ranked",
)


class SetupCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    setup_group = app_commands.Group(
        name="setup", description="Provision and verify the Shaheen server"
    )

    @setup_group.command(name="run", description="Run the interactive Shaheen setup wizard")
    @app_commands.describe(
        mode="development keeps public areas restricted; launch opens onboarding"
    )
    @require_setup_authorized()
    async def run(
        self,
        interaction: discord.Interaction,
        mode: Literal["development", "launch"] = "development",
    ) -> None:
        guild = interaction.guild
        if guild is None:
            raise SetupError("This command can only be used inside the Shaheen server.")

        me = guild.me
        if me is None or not me.guild_permissions.is_superset(REQUIRED_BOT_PERMISSIONS):
            raise SetupError(
                "Shaheen is missing Manage Roles / Manage Channels permission. "
                "Grant those to the bot's role and try again."
            )

        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            service = SetupService(guild, session)
            plan = await service.plan()

        preview = build_plan_embed(plan, mode)
        view = ConfirmView(author_id=interaction.user.id)
        message = await interaction.followup.send(
            embed=preview, view=view, ephemeral=True, wait=True
        )
        await view.wait()

        if not view.confirmed:
            await message.edit(content="Setup cancelled.", embed=None, view=None)
            return

        async with session_scope(self.bot.session_factory) as session:
            service = SetupService(guild, session)
            report = await service.apply(mode)

            if mode == "launch":
                await self._deploy_launch_messages(guild, session)

        await message.edit(content=None, embed=build_report_embed(report), view=None)

    @setup_group.command(
        name="status", description="Show whether Shaheen's expected resources exist"
    )
    @require_setup_authorized()
    async def status(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            raise SetupError("This command can only be used inside the Shaheen server.")

        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = SetupService(guild, session)
            plan = await service.plan()
            settings = await GuildSettingsRepository(session).get(guild.id)

        last_setup_at = (
            settings.last_setup_at.strftime("%Y-%m-%d %H:%M UTC")
            if settings and settings.last_setup_at
            else None
        )
        embed = build_status_embed(
            plan, mode=settings.setup_mode if settings else None, last_setup_at=last_setup_at
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @setup_group.command(
        name="verify", description="Run non-destructive validation and report discrepancies"
    )
    @require_setup_authorized()
    async def verify(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            raise SetupError("This command can only be used inside the Shaheen server.")

        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = SetupService(guild, session)
            plan = await service.plan()

        await interaction.followup.send(embed=build_verify_embed(plan), ephemeral=True)

    async def _deploy_launch_messages(self, guild: discord.Guild, session: AsyncSession) -> None:
        resources = ProvisionedResourceRepository(session)
        # Each channel can get more than one message; _already_posted's
        # title check keeps re-running /setup from duplicating any of them.
        # The persistent-view instances here are fresh objects, but that's
        # fine — discord.py routes an interaction to whichever registered
        # view has a matching custom_id (ShaheenBot.setup_hook), regardless
        # of which specific instance is attached to the message that was
        # actually sent (docs/DECISIONS.md ADR-058).
        messages_by_channel_key: dict[str, list[tuple[discord.Embed, discord.ui.View | None]]] = {
            "channel:welcome": [(build_welcome_embed(), None)],
            "channel:rules": [(build_rules_embed(), None)],
            "channel:roles": [
                (build_roles_embed(), None),
                (build_self_assign_roles_embed(), SelfAssignRolesView()),
            ],
            "channel:ranked": [(build_spar_kiosk_embed(), SparKioskView())],
        }
        for logical_key in _LAUNCH_MESSAGE_CHANNELS:
            resource = await resources.get(
                guild_id=guild.id, resource_type=ResourceType.CHANNEL, logical_key=logical_key
            )
            if resource is None:
                continue
            channel = guild.get_channel(resource.discord_id)
            if not isinstance(channel, discord.TextChannel):
                continue
            for embed, view in messages_by_channel_key[logical_key]:
                if await _already_posted(channel, embed.title, self.bot.user):
                    continue
                if view is not None:
                    await channel.send(embed=embed, view=view)
                else:
                    await channel.send(embed=embed)


async def _already_posted(
    channel: discord.TextChannel, title: str | None, bot_user: discord.ClientUser | None
) -> bool:
    if bot_user is None or title is None:
        return False
    async for message in channel.history(limit=20):
        if message.author.id == bot_user.id and message.embeds and message.embeds[0].title == title:
            return True
    return False


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(SetupCog(bot))
