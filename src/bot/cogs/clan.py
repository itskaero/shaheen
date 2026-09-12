"""Scheduled snapshots + /leaderboard, /achievements, /history.

Stays thin (docs/ARCHITECTURE.md): the snapshot job and all queries live in
services/snapshot_service.py and services/clan_service.py.
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import UTC, datetime, time, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.checks.permissions import require_staff_authorized
from bot.client import ShaheenBot
from bot.cogs.competition import resolve_provisioned_channel
from bot.constants import ROLE_MVP
from bot.content.clan_embeds import (
    build_achievement_announcement_embed,
    build_achievements_embed,
    build_history_embed,
    build_leaderboard_embed,
    build_legend_meta_embed,
    build_milestone_announcement_embed,
    build_mvp_announcement_embed,
    build_spotlight_embed,
    build_tier_change_announcement_embed,
    build_weekly_digest_embed,
)
from bot.content.profile_embeds import build_not_linked_embed
from core.exceptions import ShaheenError
from database.models.provisioned_resource import ResourceType
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope
from services.clan_service import ClanService
from services.digest_service import WeeklyDigest, WeeklyDigestService
from services.image_service import render_milestone_card
from services.link_service import LinkService
from services.snapshot_service import Announcement, SnapshotService

logger = logging.getLogger(__name__)

_HALL_OF_FAME_KEY = "channel:hall_of_fame"
_ANNOUNCEMENTS_KEY = "channel:announcements"
_DIGEST_WEEKDAY = 6  # Sunday (Monday=0 .. Sunday=6)


class ClanCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot
        # Interval is config-driven (ADR-028), so the loop is built per
        # instance rather than via the @tasks.loop class decorator.
        self.snapshot_loop = tasks.loop(hours=bot.settings.snapshot_interval_hours)(
            self._snapshot_tick
        )
        # Fires daily at a fixed UTC time and no-ops on every day but
        # Sunday, rather than tasks.loop(hours=24*7) — a 168-hour period
        # drifts against the calendar based on whenever the bot happened to
        # last restart, which a fixed daily check avoids (docs/DECISIONS.md
        # ADR-070).
        self.weekly_digest_loop = tasks.loop(time=time(hour=12, tzinfo=UTC))(
            self._weekly_digest_tick
        )

    async def cog_load(self) -> None:
        self.snapshot_loop.before_loop(self._before_snapshot_loop)
        self.snapshot_loop.start()
        self.weekly_digest_loop.before_loop(self._before_snapshot_loop)
        self.weekly_digest_loop.start()

    async def cog_unload(self) -> None:
        self.snapshot_loop.cancel()
        self.weekly_digest_loop.cancel()

    async def _before_snapshot_loop(self) -> None:
        await self.bot.wait_until_ready()

    async def _snapshot_tick(self) -> None:
        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            logger.warning("Snapshot tick skipped: guild %s not found", self.bot.settings.guild_id)
            return

        async with session_scope(self.bot.session_factory) as session:
            service = SnapshotService(session, self.bot.brawlhalla)
            result = await service.run_for_guild(guild.id)

        logger.info(
            "Snapshot cycle: %d member(s), %d error(s), %d announcement(s)",
            result.members_processed,
            len(result.errors),
            len(result.announcements),
        )
        for announcement in result.announcements:
            await self._announce(guild, announcement)

    async def _announce(self, guild: discord.Guild, announcement: Announcement) -> None:
        channel = await self._hall_of_fame_channel(guild)
        if channel is None:
            return

        member = guild.get_member(announcement.discord_id)
        display_name = member.display_name if member else announcement.player.player_name

        if announcement.achievement is not None:
            embed = build_achievement_announcement_embed(
                display_name=display_name, achievement=announcement.achievement
            )
            subtitle = f"🏅 {announcement.achievement.name}"
        elif announcement.new_peak_rating is not None:
            embed = build_milestone_announcement_embed(
                display_name=display_name,
                player_name=announcement.player.player_name,
                new_peak_rating=announcement.new_peak_rating,
            )
            subtitle = f"New peak rating: {announcement.new_peak_rating}!"
        elif announcement.tier_change is not None:
            change = announcement.tier_change
            embed = build_tier_change_announcement_embed(
                display_name=display_name,
                player_name=announcement.player.player_name,
                old_tier=change.old_tier,
                new_tier=change.new_tier,
                promoted=change.promoted,
            )
            subtitle = (
                f"Promoted to {change.new_tier}!"
                if change.promoted
                else f"Dropped to {change.new_tier}"
            )
        else:
            return

        # A branded generated card alongside the embed (docs/DECISIONS.md
        # ADR-059) — a rendering failure here should never lose the
        # announcement itself, so fall back to the plain embed. Rendering
        # is CPU-bound Pillow work over a ~1.9MB template (docs/
        # DECISIONS.md ADR-062) — run it off the event loop so it can't
        # stall the bot's heartbeat/other commands while it runs.
        file: discord.File | None = None
        try:
            png_bytes = await asyncio.to_thread(
                render_milestone_card, title=display_name, subtitle=subtitle
            )
            file = discord.File(io.BytesIO(png_bytes), filename="milestone.png")
            embed.set_image(url="attachment://milestone.png")
        except Exception:
            logger.exception("Failed to render milestone card for %s", display_name)

        try:
            if file is not None:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Missing permission to post in hall-of-fame channel")

    async def _hall_of_fame_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        async with session_scope(self.bot.session_factory) as session:
            resources = ProvisionedResourceRepository(session)
            resource = await resources.get(
                guild_id=guild.id, resource_type=ResourceType.CHANNEL, logical_key=_HALL_OF_FAME_KEY
            )
        if resource is None:
            return None
        channel = guild.get_channel(resource.discord_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    # --- weekly digest + MVP of the Week (docs/DECISIONS.md ADR-070) -------

    async def _weekly_digest_tick(self) -> None:
        if datetime.now(UTC).weekday() != _DIGEST_WEEKDAY:
            return

        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            logger.warning("Weekly digest skipped: guild %s not found", self.bot.settings.guild_id)
            return

        since = datetime.now(UTC) - timedelta(days=7)
        async with session_scope(self.bot.session_factory) as session:
            digest = await WeeklyDigestService(session).build_and_rotate(guild.id, since=since)

        await self._post_weekly_digest(guild, digest)
        if digest.mvp_discord_id is not None:
            await self._rotate_mvp_role(guild, digest.mvp_discord_id)

    async def _post_weekly_digest(self, guild: discord.Guild, digest: WeeklyDigest) -> None:
        channel = await resolve_provisioned_channel(self.bot, guild, _ANNOUNCEMENTS_KEY)
        if channel is None:
            return

        rating_gains = [
            (self._display_name(guild, g.discord_id, g.player_name), g.rating_gain)
            for g in digest.rating_gains
        ]
        top_chatters = [
            (self._display_name(guild, c.discord_id, f"<@{c.discord_id}>"), c.weekly_xp)
            for c in digest.top_chatters
        ]
        embed = build_weekly_digest_embed(
            rating_gains=rating_gains,
            top_chatters=top_chatters,
            matches_played=digest.matches_played,
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Missing permission to post in announcements channel")
            return

        if digest.mvp_discord_id is not None and digest.mvp_reason is not None:
            mvp_name = self._display_name(
                guild, digest.mvp_discord_id, f"<@{digest.mvp_discord_id}>"
            )
            mvp_embed = build_mvp_announcement_embed(
                display_name=mvp_name, reason=digest.mvp_reason
            )
            try:
                await channel.send(embed=mvp_embed)
            except discord.Forbidden:
                logger.warning("Missing permission to post MVP announcement")

    async def _rotate_mvp_role(self, guild: discord.Guild, mvp_discord_id: int) -> None:
        async with session_scope(self.bot.session_factory) as session:
            resource = await ProvisionedResourceRepository(session).get(
                guild_id=guild.id,
                resource_type=ResourceType.ROLE,
                logical_key=ROLE_MVP.logical_key,
            )
        if resource is None:
            return
        role = guild.get_role(resource.discord_id)
        if role is None:
            return

        new_mvp = guild.get_member(mvp_discord_id)
        try:
            for previous_holder in list(role.members):
                if previous_holder.id != mvp_discord_id:
                    await previous_holder.remove_roles(role, reason="Shaheen weekly digest")
            if new_mvp is not None and role not in new_mvp.roles:
                await new_mvp.add_roles(role, reason="Shaheen weekly digest")
        except discord.Forbidden:
            logger.warning("Missing permission to rotate MVP of the Week role")

    def _display_name(self, guild: discord.Guild, discord_id: int, fallback: str) -> str:
        member = guild.get_member(discord_id)
        return member.display_name if member else fallback

    @app_commands.command(
        name="spotlight", description="Feature a member in #announcements (staff only)"
    )
    @app_commands.describe(user="Who to spotlight", note="Why they're being featured")
    @require_staff_authorized()
    async def spotlight(
        self, interaction: discord.Interaction, user: discord.Member, note: str
    ) -> None:
        moderator = interaction.user
        if interaction.guild is None or not isinstance(moderator, discord.Member):
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        channel = await resolve_provisioned_channel(
            self.bot, interaction.guild, _ANNOUNCEMENTS_KEY
        )
        if channel is None:
            raise ShaheenError(
                "The announcements channel isn't set up yet — ask staff to run /setup."
            )

        embed = build_spotlight_embed(
            display_name=user.display_name, note=note, staff_name=moderator.display_name
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden as exc:
            raise ShaheenError("Missing permission to post in the announcements channel.") from exc

        await interaction.followup.send(
            f"✨ Spotlighted {user.mention} in {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="leaderboard", description="Show the Shaheen internal leaderboard")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            rows = await ClanService(session).leaderboard(interaction.guild.id)

        entries = []
        for _member, _player, discord_id, snapshot in rows:
            discord_member = interaction.guild.get_member(discord_id)
            name = discord_member.display_name if discord_member else _player.player_name
            entries.append((name, snapshot.tier, snapshot.rating))

        await interaction.followup.send(embed=build_leaderboard_embed(entries), ephemeral=True)

    @app_commands.command(
        name="achievements", description="Show a Shaheen member's earned achievements"
    )
    @app_commands.describe(user="Whose achievements to show (defaults to you)")
    async def achievements(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = await self._resolve_member(interaction, user)
        if member is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            active = await link_service.get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )
            if active is None:
                await interaction.followup.send(
                    embed=build_not_linked_embed(target_is_self=user is None), ephemeral=True
                )
                return
            shaheen_member, _player = active
            entries = await ClanService(session).achievements_for_member(shaheen_member.id)

        embed = build_achievements_embed(display_name=member.display_name, entries=entries)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="history", description="Show a Shaheen member's stored rating history"
    )
    @app_commands.describe(user="Whose history to show (defaults to you)")
    async def history(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = await self._resolve_member(interaction, user)
        if member is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            active = await link_service.get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )
            if active is None:
                await interaction.followup.send(
                    embed=build_not_linked_embed(target_is_self=user is None), ephemeral=True
                )
                return
            _shaheen_member, player = active
            snapshots = await ClanService(session).history(player.id)

        embed = build_history_embed(
            display_name=member.display_name, player_name=player.player_name, snapshots=snapshots
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="legendmeta", description="Show the clan's most-played Legends and their win rates"
    )
    async def legendmeta(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            entries = await ClanService(session).legend_meta(interaction.guild.id)

        await interaction.followup.send(embed=build_legend_meta_embed(entries), ephemeral=True)

    async def _resolve_member(
        self, interaction: discord.Interaction, user: discord.Member | None
    ) -> discord.Member | None:
        member = user or interaction.user
        if not isinstance(member, discord.Member) or interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)
        return member


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(ClanCog(bot))
