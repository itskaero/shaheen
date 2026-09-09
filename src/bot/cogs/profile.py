"""/profile, /rank, /stats, /legends.

Read-only member commands — usable by any member, no permission check
(docs/PERMISSIONS.md: "competitive/member commands should be usable by
ordinary members where appropriate").
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import ShaheenBot
from bot.content.profile_embeds import (
    build_legends_embed,
    build_not_linked_embed,
    build_profile_embed,
    build_rank_embed,
    build_stats_embed,
)
from core.exceptions import ShaheenError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.session import session_scope
from services.link_service import LinkService
from services.profile_service import ProfileService


class ProfileCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="Show a Shaheen member's Brawlhalla profile")
    @app_commands.describe(user="Whose profile to show (defaults to you)")
    async def profile(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = await self._start(interaction, user)
        if member is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            service = ProfileService(LinkService(session, self.bot.brawlhalla), self.bot.brawlhalla)
            player = await self._require_link(interaction, service, member, is_self=user is None)
            if player is None:
                return
            stats = await service.get_stats(player.brawlhalla_player_id)
            ranked = await service.get_ranked(player.brawlhalla_player_id)

        embed = build_profile_embed(
            display_name=member.display_name,
            avatar_url=member.display_avatar.url,
            player=player,
            stats=stats,
            ranked=ranked,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="rank", description="Show a Shaheen member's ranked standing")
    @app_commands.describe(user="Whose rank to show (defaults to you)")
    async def rank(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = await self._start(interaction, user)
        if member is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            service = ProfileService(LinkService(session, self.bot.brawlhalla), self.bot.brawlhalla)
            player = await self._require_link(interaction, service, member, is_self=user is None)
            if player is None:
                return
            ranked = await service.get_ranked(player.brawlhalla_player_id)

        embed = build_rank_embed(display_name=member.display_name, player=player, ranked=ranked)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="Show a Shaheen member's Brawlhalla stats")
    @app_commands.describe(user="Whose stats to show (defaults to you)")
    async def stats(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = await self._start(interaction, user)
        if member is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            service = ProfileService(LinkService(session, self.bot.brawlhalla), self.bot.brawlhalla)
            player = await self._require_link(interaction, service, member, is_self=user is None)
            if player is None:
                return
            stats = await service.get_stats(player.brawlhalla_player_id)

        embed = build_stats_embed(display_name=member.display_name, player=player, stats=stats)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="legends", description="Show a Shaheen member's per-Legend stats")
    @app_commands.describe(user="Whose Legend stats to show (defaults to you)")
    async def legends(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = await self._start(interaction, user)
        if member is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            service = ProfileService(LinkService(session, self.bot.brawlhalla), self.bot.brawlhalla)
            player = await self._require_link(interaction, service, member, is_self=user is None)
            if player is None:
                return
            stats = await service.get_stats(player.brawlhalla_player_id)

        embed = build_legends_embed(display_name=member.display_name, player=player, stats=stats)
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _start(
        self, interaction: discord.Interaction, user: discord.Member | None
    ) -> discord.Member | None:
        """Defers the interaction and resolves the target member, or None on error."""
        member = user or interaction.user
        if not isinstance(member, discord.Member) or interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)
        return member

    async def _require_link(
        self,
        interaction: discord.Interaction,
        service: ProfileService,
        member: discord.Member,
        *,
        is_self: bool,
    ) -> BrawlhallaPlayer | None:
        linked = await service.get_linked_player(guild_id=member.guild.id, discord_id=member.id)
        if linked is None:
            await interaction.followup.send(
                embed=build_not_linked_embed(target_is_self=is_self), ephemeral=True
            )
            return None
        return linked[1]


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(ProfileCog(bot))
