"""Chat XP/leveling + welcome/leave messages (docs/DECISIONS.md ADR-065).

Stays thin (docs/ARCHITECTURE.md): the XP curve/rank titles live in
services/chat_gamification.py (pure logic), persistence in database/
repositories/chat_activity_repository.py, and Discord-facing card
rendering reuses services/image_service.py's welcome/goodbye/milestone
renderers exactly the way bot/cogs/clan.py's _announce reuses
render_milestone_card. No permission check on /level or /chatboard —
same "any member" posture as /profile.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import ShaheenBot
from bot.cogs.competition import resolve_provisioned_channel
from bot.constants import ROLE_GUEST
from bot.content.engagement_embeds import (
    build_chatboard_embed,
    build_level_embed,
    build_level_up_embed,
)
from core.exceptions import ShaheenError
from database.models.provisioned_resource import ResourceType
from database.repositories.chat_activity_repository import ChatActivityRepository
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope
from services.chat_gamification import (
    MESSAGE_XP_COOLDOWN_SECONDS,
    level_for_xp,
    roll_message_xp,
)
from services.image_service import render_goodbye_card, render_milestone_card, render_welcome_card

logger = logging.getLogger(__name__)

_WELCOME_KEY = "channel:welcome"
_HALL_OF_FAME_KEY = "channel:hall_of_fame"


class EngagementCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    # --- chat XP -------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        discord_id = message.author.id
        now = datetime.now(UTC)
        new_level: int | None = None

        async with session_scope(self.bot.session_factory) as session:
            repo = ChatActivityRepository(session)
            existing = await repo.get(guild_id=guild_id, discord_id=discord_id)
            if existing is not None and existing.last_xp_at is not None:
                elapsed = (now - existing.last_xp_at).total_seconds()
                if elapsed < MESSAGE_XP_COOLDOWN_SECONDS:
                    return

            old_level = existing.level if existing is not None else 1
            row = await repo.record_message(
                guild_id=guild_id, discord_id=discord_id, xp_gain=roll_message_xp(), now=now
            )
            computed_level = level_for_xp(row.xp)
            if computed_level > old_level:
                row.level = computed_level
                new_level = computed_level

        if new_level is not None and isinstance(message.author, discord.Member):
            await self._announce_level_up(message.guild, message.author, new_level)

    async def _announce_level_up(
        self, guild: discord.Guild, member: discord.Member, level: int
    ) -> None:
        channel = await resolve_provisioned_channel(self.bot, guild, _HALL_OF_FAME_KEY)
        if channel is None:
            return

        embed = build_level_up_embed(mention=member.mention, level=level)
        file: discord.File | None = None
        try:
            png_bytes = await asyncio.to_thread(
                render_milestone_card, title=member.display_name, subtitle=f"Level {level} reached!"
            )
            file = discord.File(io.BytesIO(png_bytes), filename="levelup.png")
            embed.set_image(url="attachment://levelup.png")
        except Exception:
            logger.exception("Failed to render level-up card for %s", member.display_name)

        try:
            if file is not None:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Missing permission to post in hall-of-fame channel")

    @app_commands.command(name="level", description="Show a member's chat level")
    @app_commands.describe(user="Whose level to show (defaults to you)")
    async def level(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = user or interaction.user
        if not isinstance(member, discord.Member) or interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            row = await ChatActivityRepository(session).get(
                guild_id=member.guild.id, discord_id=member.id
            )

        xp = row.xp if row else 0
        # Derived live from xp, not the stored `level` column — see the
        # same note in services/website_service.py's get_community_activity.
        level_value = level_for_xp(xp)
        embed = build_level_embed(display_name=member.display_name, xp=xp, level=level_value)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="chatboard", description="Show the most active chatters")
    async def chatboard(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            rows = await ChatActivityRepository(session).list_top(interaction.guild.id, limit=10)

        entries = []
        for row in rows:
            discord_member = interaction.guild.get_member(row.discord_id)
            name = discord_member.display_name if discord_member else f"<@{row.discord_id}>"
            # Derived live from xp — see the note in /level above.
            entries.append((name, level_for_xp(row.xp), row.xp))

        await interaction.followup.send(embed=build_chatboard_embed(entries), ephemeral=True)

    # --- welcome / leave -------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self._assign_guest_role(member)
        await self._post_arrival_card(member.guild, member=member, joining=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self._post_arrival_card(member.guild, member=member, joining=False)

    async def _assign_guest_role(self, member: discord.Member) -> None:
        async with session_scope(self.bot.session_factory) as session:
            resource = await ProvisionedResourceRepository(session).get(
                guild_id=member.guild.id,
                resource_type=ResourceType.ROLE,
                logical_key=ROLE_GUEST.logical_key,
            )
        if resource is None:
            return
        role = member.guild.get_role(resource.discord_id)
        if role is None:
            return
        try:
            await member.add_roles(role, reason="Auto-assigned on join (docs/DECISIONS.md ADR-065)")
        except discord.Forbidden:
            logger.warning("Missing permission to assign Guest role to %s", member.id)

    async def _post_arrival_card(
        self, guild: discord.Guild, *, member: discord.Member | discord.User, joining: bool
    ) -> None:
        channel = await resolve_provisioned_channel(self.bot, guild, _WELCOME_KEY)
        if channel is None:
            return

        renderer = render_welcome_card if joining else render_goodbye_card
        filename = "welcome.png" if joining else "goodbye.png"
        content = (
            f"{member.mention} just joined — check 📜-rules, then run `/link` to get started!"
            if joining
            else f"{member.display_name} has left Shaheen."
        )

        file: discord.File | None = None
        try:
            png_bytes = await asyncio.to_thread(renderer, member_name=member.display_name)
            file = discord.File(io.BytesIO(png_bytes), filename=filename)
        except Exception:
            logger.exception(
                "Failed to render %s card for %s", "welcome" if joining else "goodbye", member.id
            )

        with contextlib.suppress(discord.Forbidden):
            if file is not None:
                await channel.send(content=content, file=file)
            else:
                await channel.send(content=content)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(EngagementCog(bot))
