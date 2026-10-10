"""/coach — coaching in BRAWLISTAN (docs/DECISIONS.md ADR-126).

Thin: rules live in services/coaching_service.py. The Coach role (given by
hand) decides who coaches; the bot mirrors its holders into the directory
when roles change and every half hour. Members ask a coach with
/coach request, which posts a card in the coaching channel with Accept and
Decline buttons for that coach. The buttons survive restarts (a DynamicItem
keyed by the request id). The bot never edits roles or channel permissions
here.
"""

from __future__ import annotations

import contextlib
import logging
import re
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.checks.permissions import check_staff_authorized, require_setup_authorized
from bot.client import ShaheenBot
from bot.content.coaching_embeds import (
    build_coach_list_embed,
    build_coach_profile_embed,
    build_open_requests_embed,
    build_request_card,
    coaches_view,
)
from core.exceptions import ShaheenError
from database.session import session_scope
from services.coaching_service import CoachingService, RoleHolder

logger = logging.getLogger(__name__)

SYNC_MINUTES = 30


def _member(interaction: discord.Interaction) -> discord.Member:
    member = interaction.user
    if not isinstance(member, discord.Member):
        raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
    return member


def _bot(interaction: discord.Interaction) -> ShaheenBot:
    client = interaction.client
    assert isinstance(client, ShaheenBot)
    return client


class CoachingDecision(
    discord.ui.DynamicItem[discord.ui.Button[discord.ui.View]],
    template=r"coach:req:(?P<id>\d+):(?P<action>accept|decline)",
):
    """Accept/Decline on a request card. Only the coach asked (or staff)."""

    def __init__(self, request_id: int, action: str) -> None:
        accept = action == "accept"
        super().__init__(
            discord.ui.Button(
                label="Accept" if accept else "Decline",
                style=discord.ButtonStyle.success if accept else discord.ButtonStyle.secondary,
                emoji="✅" if accept else None,
                custom_id=f"coach:req:{request_id}:{action}",
            )
        )
        self.request_id = request_id
        self.accept = accept

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Item[Any],
        match: re.Match[str],
        /,
    ) -> CoachingDecision:
        return cls(int(match["id"]), match["action"])

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = _bot(interaction)
        member = interaction.user
        if not isinstance(member, discord.Member):
            return
        is_staff = check_staff_authorized(member, bot.settings.bot_owner_id)
        try:
            async with session_scope(bot.session_factory) as session:
                request, coach = await CoachingService(session).respond(
                    request_id=self.request_id,
                    actor_discord_id=member.id,
                    accept=self.accept,
                    is_staff=is_staff,
                )
                card = build_request_card(request, coach, actor_id=member.id)
                student_id, coach_id = request.student_discord_id, coach.discord_id
        except ShaheenError as exc:
            await interaction.response.send_message(f"⚠️ {exc}", ephemeral=True)
            return
        await interaction.response.edit_message(embed=card, view=None)
        logger.info(
            "Coaching request #%s %s by %s",
            self.request_id,
            "accepted" if self.accept else "declined",
            member.id,
        )
        if self.accept:
            await interaction.followup.send(
                f"<@{student_id}>, <@{coach_id}> accepted your coaching request. "
                "Sort out a time together here or in DMs.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            return
        student = interaction.guild.get_member(student_id) if interaction.guild else None
        if student is not None:
            # DMs may be closed; the card shows the outcome either way.
            with contextlib.suppress(discord.HTTPException):
                await student.send(
                    f"Your coaching request #{self.request_id} wasn't taken this time. "
                    "Try another coach from `/coach list`."
                )


def request_view(request_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(CoachingDecision(request_id, "accept"))
    view.add_item(CoachingDecision(request_id, "decline"))
    return view


class CoachingCog(commands.Cog):
    coach = app_commands.Group(name="coach", description="Coaches and coaching requests")

    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot
        self.sync_loop = tasks.loop(minutes=SYNC_MINUTES)(self._sync_tick)

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(CoachingDecision)
        self.sync_loop.before_loop(self.bot.wait_until_ready)
        self.sync_loop.start()

    async def cog_unload(self) -> None:
        self.sync_loop.cancel()
        self.bot.remove_dynamic_items(CoachingDecision)

    # --- mirroring the Coach role -------------------------------------------

    async def _sync(self, guild: discord.Guild) -> None:
        async with session_scope(self.bot.session_factory) as session:
            service = CoachingService(session)
            config = await service.config(guild.id)
            role = guild.get_role(config.role_id) if config.role_id else None
            if role is None:
                return
            holders = [
                RoleHolder(discord_id=m.id, display_name=m.display_name)
                for m in role.members
                if not m.bot
            ]
            result = await service.sync(guild.id, holders)
        if result.changed:
            logger.info(
                "Coach sync: %d added, %d back, %d removed",
                result.added,
                result.reactivated,
                result.deactivated,
            )

    async def _sync_tick(self) -> None:
        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            return
        try:
            await self._sync(guild)
        except Exception:
            logger.exception("Coach sync failed")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.roles == after.roles:
            return
        changed = set(before.roles) ^ set(after.roles)
        try:
            async with session_scope(self.bot.session_factory) as session:
                config = await CoachingService(session).config(after.guild.id)
            if config.role_id is not None and any(r.id == config.role_id for r in changed):
                await self._sync(after.guild)
        except Exception:
            logger.exception("Coach sync after a role change failed")

    # --- anyone -------------------------------------------------------------

    @coach.command(name="list", description="The BRAWLISTAN coaches")
    async def list_coaches(self, interaction: discord.Interaction) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            entries = await CoachingService(session).directory(member.guild.id)
            embed = build_coach_list_embed(entries, site_url=self.bot.settings.site_url)
        await interaction.followup.send(
            embed=embed, view=coaches_view(self.bot.settings.site_url), ephemeral=True
        )

    @coach.command(name="request", description="Ask a coach for a coaching session")
    @app_commands.describe(
        coach="The coach (see /coach list)",
        message="What you'd like help with: legend, matchup, rank goal…",
    )
    async def request(
        self,
        interaction: discord.Interaction,
        coach: discord.Member,
        message: app_commands.Range[str, 10, 280],
    ) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = CoachingService(session)
            config = await service.config(member.guild.id)
            channel = member.guild.get_channel(config.channel_id) if config.channel_id else None
            if not isinstance(channel, discord.TextChannel):
                raise ShaheenError("Coaching requests aren't open yet: staff run /coach setup.")
            row, coach_row = await service.request(
                guild_id=member.guild.id,
                coach_discord_id=coach.id,
                student_discord_id=member.id,
                message=message,
            )
            try:
                posted = await channel.send(
                    content=f"<@{coach.id}>, new coaching request from <@{member.id}>",
                    embed=build_request_card(row, coach_row),
                    view=request_view(row.id),
                    allowed_mentions=discord.AllowedMentions(users=[coach]),
                )
            except discord.HTTPException as exc:
                # Rolls the request back with the session.
                raise ShaheenError(
                    "Couldn't post in the coaching channel; ask staff to check the bot can "
                    "send messages there."
                ) from exc
            await service.mark_posted(row, posted.id)
            request_id = row.id
        logger.info("Coaching request #%s to %s by %s", request_id, coach.id, member.id)
        await interaction.followup.send(
            f"✅ Request #{request_id} sent to {coach.mention} in {channel.mention}. "
            "You'll be pinged when they answer.",
            ephemeral=True,
        )

    # --- coaches ------------------------------------------------------------

    @coach.command(name="requests", description="Your open coaching requests (coaches)")
    async def requests(self, interaction: discord.Interaction) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = CoachingService(session)
            coach = await service.coach_of(member.guild.id, member.id)
            if coach is None:
                raise ShaheenError("Only coaches have requests. Staff give the Coach role.")
            embed = build_open_requests_embed(await service.open_for_coach(coach))
        await interaction.followup.send(embed=embed, ephemeral=True)

    @coach.command(name="profile", description="Edit your coach profile (coaches)")
    @app_commands.describe(
        specialty="What you teach best, e.g. 'Sword fundamentals' (empty text clears)",
        legends="Up to 3 legends, comma-separated",
        availability="When you coach, e.g. 'Weekends, 8–11 PM PKT'",
        bio="A line or two about you",
        accepting="Taking new students?",
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        specialty: app_commands.Range[str, 0, 80] | None = None,
        legends: app_commands.Range[str, 0, 80] | None = None,
        availability: app_commands.Range[str, 0, 80] | None = None,
        bio: app_commands.Range[str, 0, 280] | None = None,
        accepting: bool | None = None,
    ) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = CoachingService(session)
            coach = await service.coach_of(member.guild.id, member.id)
            if coach is None:
                raise ShaheenError("Only coaches have a profile. Staff give the Coach role.")
            coach = await service.update_profile(
                coach,
                specialty=specialty,
                legends=legends,
                availability=availability,
                bio=bio,
                accepting=accepting,
            )
            embed = build_coach_profile_embed(coach)
        await interaction.followup.send(
            "Saved. The website updates within a few hours.", embed=embed, ephemeral=True
        )

    # --- setup --------------------------------------------------------------

    @coach.command(name="setup", description="Set the Coach role and the coaching channel (admin)")
    @app_commands.describe(
        role="The role your coaches hold (given by hand)",
        channel="Where coaching requests are posted",
    )
    @require_setup_authorized()
    async def setup_coaching(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        channel: discord.TextChannel,
    ) -> None:
        member = _member(interaction)
        if role.is_default() or role.managed:
            raise ShaheenError("Pick the role your coaches actually hold.")
        me = member.guild.me
        perms = channel.permissions_for(me) if me else None
        if perms is None or not (perms.send_messages and perms.embed_links):
            raise ShaheenError(
                f"The bot can't post embeds in {channel.mention}. Allow it Send Messages and "
                "Embed Links there, then run this again."
            )
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            await CoachingService(session).set_config(
                member.guild.id, role_id=role.id, channel_id=channel.id, staff_discord_id=member.id
            )
        await self._sync(member.guild)
        coaches = sum(1 for m in role.members if not m.bot)
        logger.info("/coach setup by %s", member.id)
        await interaction.followup.send(
            f"✅ Coaches are members with {role.mention} ({coaches} now). Requests go to "
            f"{channel.mention}. Coaches fill in their profile with `/coach profile`.",
            ephemeral=True,
        )


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(CoachingCog(bot))
