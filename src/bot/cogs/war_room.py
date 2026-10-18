"""The war room (docs/DECISIONS.md ADR-136): Clan Wars and City Wars, live in
one channel.

`/warroom setup` points it at a channel. Every 15 minutes the bot edits one
pinned scoreboard there and, at most once each, posts:
- a lead change when another clan takes first place;
- a countdown in the last six hours of the week;
- the Monday verdict: final standings, duels, the MVP (pinged only if they
  have linked) and a shareable result card.
Rules and state live in services/war_room*.py; this is the Discord side.
"""

from __future__ import annotations

import contextlib
import io
import logging
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy.ext.asyncio import AsyncSession

from bot.checks.permissions import require_setup_authorized
from bot.client import ShaheenBot
from bot.content.war_room_embeds import (
    build_countdown_embed,
    build_lead_change_text,
    build_scoreboard_embed,
    build_verdict_embed,
)
from core.exceptions import ShaheenError
from database.session import session_scope
from services.clan_war_service import WarWeek
from services.image_service import render_clan_war_card
from services.quests import week_bounds
from services.war_room import WarRoomState
from services.war_room_service import WarRoomService

logger = logging.getLogger(__name__)

TICK_MINUTES = 15


def _card(week: WarWeek, site_url: str) -> bytes:
    scored = [t for t in week.standings if t.points > 0]
    mvp = week.mvp
    return render_clan_war_card(
        week_label=f"week of {week.week_start.strftime('%-d %b')}",
        standings=[(t.team.name, t.team.tag, t.points, t.team.accent) for t in scored],
        mvp=(mvp.player.player_name, mvp.points, mvp.team.tag if mvp.team else None)
        if mvp
        else None,
        site=f"{site_url.removeprefix('https://').rstrip('/')}/clanwars.html",
    )


class WarRoomCog(commands.Cog):
    warroom = app_commands.Group(
        name="warroom", description="The live Clan Wars + City Wars channel"
    )

    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot
        self.loop = tasks.loop(minutes=TICK_MINUTES)(self._tick_all)

    async def cog_load(self) -> None:
        self.loop.before_loop(self.bot.wait_until_ready)
        self.loop.start()

    async def cog_unload(self) -> None:
        self.loop.cancel()

    def _service(self, session: AsyncSession) -> WarRoomService:
        return WarRoomService(session, min_games=self.bot.settings.clan_wars_min_games)

    async def _tick_all(self) -> None:
        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            return
        try:
            await self.tick(guild)
        except Exception:
            logger.exception("War room tick failed")

    async def tick(self, guild: discord.Guild) -> None:
        async with session_scope(self.bot.session_factory) as session:
            service = self._service(session)
            config = await service.config(guild.id)
            if config.channel_id is None:
                return
            view = await service.view(guild.id)
        channel = guild.get_channel(config.channel_id)
        if not isinstance(channel, discord.TextChannel):
            logger.warning("War room channel %s not found", config.channel_id)
            return
        site = self.bot.settings.site_url
        now = datetime.now(UTC)

        message_id = await self._update_scoreboard(
            channel,
            config.message_id,
            build_scoreboard_embed(week=view.week, cities=view.cities, site_url=site, now=now),
        )
        plan = view.plan
        none = discord.AllowedMentions.none()
        try:
            if plan.lead_change is not None:
                text = build_lead_change_text(
                    week=view.week, old_leader=plan.lead_change[0], new_leader=plan.lead_change[1]
                )
                if text:
                    await channel.send(text, allowed_mentions=none)
            if plan.countdown:
                await channel.send(embed=build_countdown_embed(week=view.week, site_url=site))
        except discord.HTTPException as exc:
            logger.warning("War room post failed: %s", exc)

        mvp_discord_id: int | None = None
        if plan.verdict and view.finished is not None and view.finished.mvp is not None:
            async with session_scope(self.bot.session_factory) as session:
                mvp_discord_id = await self._service(session).award_mvp(
                    guild.id, view.finished.mvp.player.id
                )
        if plan.verdict and view.finished is not None:
            await self._post_verdict(channel, view.finished, mvp_discord_id)

        async with session_scope(self.bot.session_factory) as session:
            service = self._service(session)
            await service.save_state(guild.id, plan.state)
            if message_id != config.message_id:
                await service.set_message(guild.id, message_id)

    async def _update_scoreboard(
        self, channel: discord.TextChannel, message_id: int | None, embed: discord.Embed
    ) -> int | None:
        """Edit the pinned scoreboard, or post and pin a new one."""
        if message_id is not None:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
                return message_id
            except discord.NotFound:
                pass
            except discord.HTTPException as exc:
                logger.warning("War room scoreboard edit failed: %s", exc)
                return message_id
        try:
            message = await channel.send(embed=embed)
        except discord.HTTPException as exc:
            logger.warning("War room scoreboard not posted: %s", exc)
            return message_id
        # Pinning needs Manage Messages; the scoreboard still works without it.
        with contextlib.suppress(discord.HTTPException):
            await message.pin(reason="BRAWLISTAN war room scoreboard")
        return message.id

    async def _post_verdict(
        self, channel: discord.TextChannel, week: WarWeek, mvp_discord_id: int | None
    ) -> None:
        site = self.bot.settings.site_url
        mention = f"<@{mvp_discord_id}>" if mvp_discord_id else None
        embed = build_verdict_embed(week=week, site_url=site, mvp_mention=mention)
        try:
            card = discord.File(io.BytesIO(_card(week, site)), filename="clan-wars.png")
        except Exception:
            logger.exception("Clan Wars card failed; posting text only")
            embed.set_image(url=None)
            card = None
        allowed = discord.AllowedMentions(
            users=[discord.Object(mvp_discord_id)] if mvp_discord_id else False,
            roles=False,
            everyone=False,
        )
        try:
            if card is not None:
                await channel.send(
                    content=mention, embed=embed, file=card, allowed_mentions=allowed
                )
            else:
                await channel.send(content=mention, embed=embed, allowed_mentions=allowed)
        except discord.HTTPException as exc:
            logger.warning("War room verdict not posted: %s", exc)

    # --- commands --------------------------------------------------------------

    @warroom.command(name="setup", description="Run the live war room in a channel (admin)")
    @app_commands.describe(channel="Where the scoreboard and war posts go")
    @require_setup_authorized()
    async def setup_war_room(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        guild = interaction.guild
        if guild is None:
            raise ShaheenError("This only works inside the BRAWLISTAN server.")
        perms = channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.embed_links and perms.attach_files):
            raise ShaheenError(
                f"I need Send Messages, Embed Links and Attach Files in {channel.mention}."
            )
        await interaction.response.defer(ephemeral=True)
        now = datetime.now(UTC)
        last_monday, _s, _e = week_bounds(now - timedelta(days=7))
        async with session_scope(self.bot.session_factory) as session:
            service = self._service(session)
            await service.set_channel(guild.id, channel.id)
            # Start fresh: no lead-change post for the current leader, and no
            # verdict for a week that ended before the war room existed.
            await service.save_state(guild.id, WarRoomState(verdict_week=last_monday))
        await self.tick(guild)
        note = "" if perms.manage_messages else " (give me Manage Messages to pin the scoreboard)"
        await interaction.followup.send(
            f"⚔️ The war room is live in {channel.mention}{note}. It updates every "
            f"{TICK_MINUTES} minutes; lead changes, the Sunday countdown and the Monday "
            "verdict post there.",
            ephemeral=True,
        )

    @warroom.command(name="off", description="Stop the war room (admin)")
    @require_setup_authorized()
    async def war_room_off(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            raise ShaheenError("This only works inside the BRAWLISTAN server.")
        async with session_scope(self.bot.session_factory) as session:
            await self._service(session).set_channel(guild.id, None)
        await interaction.response.send_message("The war room is off.", ephemeral=True)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(WarRoomCog(bot))
