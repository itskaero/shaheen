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
from bot.content.channel_intros import (
    build_announcements_intro_embed,
    build_bot_testing_intro_embed,
    build_brawlhalla_intro_embed,
    build_bug_reports_intro_embed,
    build_clan_info_intro_embed,
    build_clips_intro_embed,
    build_commands_intro_embed,
    build_development_log_intro_embed,
    build_general_intro_embed,
    build_hall_of_fame_intro_embed,
    build_leaderboard_intro_embed,
    build_legend_talk_intro_embed,
    build_memes_intro_embed,
    build_mod_log_intro_embed,
    build_one_v_one_intro_embed,
    build_pakistan_chat_intro_embed,
    build_scrims_intro_embed,
    build_suggestions_intro_embed,
    build_tips_guides_intro_embed,
    build_tournaments_intro_embed,
    build_two_v_two_intro_embed,
    build_website_testing_intro_embed,
)
from bot.content.competition_embeds import build_spar_kiosk_embed
from bot.content.embeds import (
    build_plan_embed,
    build_report_embed,
    build_reset_report_embed,
    build_reset_warning_embed,
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

_RESET_CONFIRM_TEXT = "DELETE"

logger = logging.getLogger(__name__)

REQUIRED_BOT_PERMISSIONS = discord.Permissions(
    manage_roles=True, manage_channels=True, view_channel=True
)

# Channels that get one or more branded messages deployed in launch mode
# (see _deploy_launch_messages for what each one gets). Every text channel
# in bot/constants.py's CATEGORIES gets something (docs/DECISIONS.md
# ADR-059) except #voice channels (no messages) and #development's admin
# channels are included too, same as the rest — they're just hidden from
# regular members by the category's own restricted=True permissions.
_LAUNCH_MESSAGE_CHANNELS: tuple[str, ...] = (
    "channel:announcements",
    "channel:welcome",
    "channel:rules",
    "channel:roles",
    "channel:clan_info",
    "channel:suggestions",
    "channel:general",
    "channel:pakistan_chat",
    "channel:memes",
    "channel:clips",
    "channel:brawlhalla",
    "channel:tips_guides",
    "channel:legend_talk",
    "channel:one_v_one",
    "channel:two_v_two",
    "channel:ranked",
    "channel:scrims",
    "channel:tournaments",
    "channel:leaderboard",
    "channel:hall_of_fame",
    "channel:bot_testing",
    "channel:website_testing",
    "channel:commands",
    "channel:bug_reports",
    "channel:development_log",
    "channel:mod_log",
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

    @setup_group.command(
        name="reset",
        description="DESTRUCTIVE: delete everything /setup created, for a clean restart",
    )
    @require_setup_authorized()
    async def reset(self, interaction: discord.Interaction) -> None:
        """Separate from /setup run on purpose (docs/DECISIONS.md ADR-060):
        /setup run stays the safe, idempotent, never-deletes-anything
        command people re-run routinely. This one permanently deletes
        every bot-created role/category/channel, so it needs its own
        explicit command name and its own, stronger confirmation — a
        warning screen, then a modal that requires typing "DELETE".
        """
        guild = interaction.guild
        if guild is None:
            raise SetupError("This command can only be used inside the Shaheen server.")

        view = _ResetWarningView(author_id=interaction.user.id, bot=self.bot, guild=guild)
        await interaction.response.send_message(
            embed=build_reset_warning_embed(), view=view, ephemeral=True
        )

    async def _deploy_launch_messages(self, guild: discord.Guild, session: AsyncSession) -> None:
        resources = ProvisionedResourceRepository(session)
        messages_by_channel_key = _launch_messages()
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
                try:
                    if await _already_posted(channel, embed.title, self.bot.user):
                        continue
                    if view is not None:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                except discord.HTTPException as exc:
                    # A missing permission, a channel deleted mid-run, a
                    # rate limit, etc. must not abort every other channel's
                    # content — log and move on (docs/DECISIONS.md ADR-059:
                    # explicit fail-safety ask). A manually *deleted
                    # message* was already safe before this — _already_posted
                    # just won't find it and re-posts normally next run.
                    logger.warning(
                        "Couldn't post launch message to %s (%s): %s",
                        logical_key,
                        channel.id,
                        exc,
                    )


def _launch_messages() -> dict[str, list[tuple[discord.Embed, discord.ui.View | None]]]:
    """One or more branded messages per channel, deployed in launch mode.

    Module-level (not inlined in _deploy_launch_messages) so
    tests/test_setup_launch_messages.py can check every text channel in
    bot.constants.CATEGORIES has an entry here without needing a live
    guild/session (docs/DECISIONS.md ADR-059). Each channel can get more
    than one message; _already_posted's title check keeps re-running
    /setup from duplicating any of them. The persistent-view instances
    here are fresh objects, but that's fine — discord.py routes an
    interaction to whichever registered view has a matching custom_id
    (ShaheenBot.setup_hook), regardless of which specific instance is
    attached to the message that was actually sent (ADR-058).
    """
    return {
        "channel:announcements": [(build_announcements_intro_embed(), None)],
        "channel:welcome": [(build_welcome_embed(), None)],
        "channel:rules": [(build_rules_embed(), None)],
        "channel:roles": [
            (build_roles_embed(), None),
            (build_self_assign_roles_embed(), SelfAssignRolesView()),
        ],
        "channel:clan_info": [(build_clan_info_intro_embed(), None)],
        "channel:suggestions": [(build_suggestions_intro_embed(), None)],
        "channel:general": [(build_general_intro_embed(), None)],
        "channel:pakistan_chat": [(build_pakistan_chat_intro_embed(), None)],
        "channel:memes": [(build_memes_intro_embed(), None)],
        "channel:clips": [(build_clips_intro_embed(), None)],
        "channel:brawlhalla": [(build_brawlhalla_intro_embed(), None)],
        "channel:tips_guides": [(build_tips_guides_intro_embed(), None)],
        "channel:legend_talk": [(build_legend_talk_intro_embed(), None)],
        "channel:one_v_one": [(build_one_v_one_intro_embed(), None)],
        "channel:two_v_two": [(build_two_v_two_intro_embed(), None)],
        "channel:ranked": [(build_spar_kiosk_embed(), SparKioskView())],
        "channel:scrims": [(build_scrims_intro_embed(), None)],
        "channel:tournaments": [(build_tournaments_intro_embed(), None)],
        "channel:leaderboard": [(build_leaderboard_intro_embed(), None)],
        "channel:hall_of_fame": [(build_hall_of_fame_intro_embed(), None)],
        "channel:bot_testing": [(build_bot_testing_intro_embed(), None)],
        "channel:website_testing": [(build_website_testing_intro_embed(), None)],
        "channel:commands": [(build_commands_intro_embed(), None)],
        "channel:bug_reports": [(build_bug_reports_intro_embed(), None)],
        "channel:development_log": [(build_development_log_intro_embed(), None)],
        "channel:mod_log": [(build_mod_log_intro_embed(), None)],
    }


async def _already_posted(
    channel: discord.TextChannel, title: str | None, bot_user: discord.ClientUser | None
) -> bool:
    if bot_user is None or title is None:
        return False
    async for message in channel.history(limit=20):
        if message.author.id == bot_user.id and message.embeds and message.embeds[0].title == title:
            return True
    return False


class _ResetWarningView(discord.ui.View):
    """Step 1 of /setup reset's two-step confirmation (docs/DECISIONS.md
    ADR-060): a plain button here, since Discord requires send_modal to be
    the direct response to the interaction that triggers it — the modal
    itself (step 2) is where the actual "type DELETE" check happens.
    """

    def __init__(self, *, author_id: int, bot: ShaheenBot, guild: discord.Guild) -> None:
        super().__init__(timeout=120)
        self._author_id = author_id
        self._bot = bot
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
        await interaction.response.send_modal(_ResetConfirmModal(self._bot, self._guild))
        self.stop()


class _ResetConfirmModal(discord.ui.Modal, title="Confirm Full Reset"):
    confirmation: discord.ui.TextInput = discord.ui.TextInput(
        label=f'Type "{_RESET_CONFIRM_TEXT}" to confirm',
        placeholder=_RESET_CONFIRM_TEXT,
        max_length=16,
    )

    def __init__(self, bot: ShaheenBot, guild: discord.Guild) -> None:
        super().__init__()
        self._bot = bot
        self._guild = guild

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.confirmation.value.strip() != _RESET_CONFIRM_TEXT:
            await interaction.response.send_message(
                f"Reset cancelled — you must type `{_RESET_CONFIRM_TEXT}` exactly.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        async with session_scope(self._bot.session_factory) as session:
            report = await SetupService(self._guild, session).reset()
        await interaction.followup.send(embed=build_reset_report_embed(report), ephemeral=True)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(SetupCog(bot))
