"""Staff commands (docs/DECISIONS.md ADR-111): /announce, /feature, /sync.

Thin: the featured-player rule lives in services/featured_service.py and
every action is audit-logged. /announce and /feature are staff
(Founder/Admin/Moderator); /sync is setup-level (Founder/Admin).
"""

from __future__ import annotations

import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import require_setup_authorized, require_staff_authorized
from bot.client import ShaheenBot
from bot.cogs.competition import resolve_provisioned_channel
from bot.constants import CHANNEL_ANNOUNCEMENTS
from bot.content.network_embeds import build_announcement_embed, build_featured_embed
from bot.views.confirm import ConfirmView
from core.exceptions import ShaheenError
from database.repositories.audit_log_repository import AuditLogRepository
from database.session import session_scope
from services.featured_service import FeaturedService
from services.link_service import LinkService

logger = logging.getLogger(__name__)

_PINGS = {
    "none": discord.AllowedMentions.none(),
    "here": discord.AllowedMentions(everyone=True, users=False, roles=False),
    "everyone": discord.AllowedMentions(everyone=True, users=False, roles=False),
}


def _staff(interaction: discord.Interaction) -> discord.Member:
    member = interaction.user
    if not isinstance(member, discord.Member):
        raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
    return member


class StaffCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(name="announce", description="Post an announcement (staff)")
    @app_commands.describe(
        title="Headline",
        message="The announcement text",
        ping="Who to notify (default: nobody)",
    )
    @require_staff_authorized()
    async def announce(
        self,
        interaction: discord.Interaction,
        title: app_commands.Range[str, 1, 200],
        message: app_commands.Range[str, 1, 2000],
        ping: Literal["none", "here", "everyone"] = "none",
    ) -> None:
        staff = _staff(interaction)
        channel = await resolve_provisioned_channel(
            self.bot, staff.guild, CHANNEL_ANNOUNCEMENTS.logical_key
        )
        if channel is None:
            raise ShaheenError(
                "There's no #announcements channel — run /setup run or set ANNOUNCEMENT_CHANNEL_ID."
            )
        embed = build_announcement_embed(title=title, message=message, author=staff.display_name)

        view = ConfirmView(author_id=staff.id)
        await interaction.response.send_message(
            content=f"Preview — post to {channel.mention}"
            + ("" if ping == "none" else f" with @{ping}")
            + "?",
            embed=embed,
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.confirmed:
            await interaction.edit_original_response(
                content="Announcement cancelled.", embed=None, view=None
            )
            return
        try:
            await channel.send(
                content=None if ping == "none" else f"@{ping}",
                embed=embed,
                allowed_mentions=_PINGS[ping],
            )
        except discord.Forbidden as exc:
            raise ShaheenError(f"I can't post in {channel.mention}.") from exc
        async with session_scope(self.bot.session_factory) as session:
            await AuditLogRepository(session).add(
                guild_id=staff.guild.id,
                action="announce",
                source="discord",
                actor_discord_id=staff.id,
                subject=title,
                detail={"ping": ping},
            )
        await interaction.edit_original_response(content="Posted.", embed=None, view=None)

    @app_commands.command(name="feature", description="Set the website's Featured Player (staff)")
    @app_commands.describe(
        user="A linked member to feature",
        brawlhalla_id="Or a tracked player's Brawlhalla ID",
        note="Why they're featured (shown on the site)",
        clear="Remove the featured player instead",
    )
    @require_staff_authorized()
    async def feature(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
        brawlhalla_id: app_commands.Range[int, 1, 10**12] | None = None,
        note: app_commands.Range[str, 1, 140] | None = None,
        clear: bool = False,
    ) -> None:
        staff = _staff(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = FeaturedService(session)
            if clear:
                await service.clear(guild_id=staff.guild.id, staff_discord_id=staff.id)
                await interaction.followup.send("Featured player cleared.", ephemeral=True)
                return
            if user is not None:
                link = await LinkService(session, self.bot.brawlhalla).get_active_link(
                    guild_id=staff.guild.id, discord_id=user.id
                )
                if link is None:
                    raise ShaheenError(f"{user.display_name} hasn't linked a Brawlhalla account.")
                brawlhalla_id = link[1].brawlhalla_player_id
            if brawlhalla_id is None:
                raise ShaheenError("Pick a member or give a Brawlhalla ID.")
            player = await service.set(
                guild_id=staff.guild.id,
                brawlhalla_id=brawlhalla_id,
                note=note,
                staff_discord_id=staff.id,
            )
            player_name, player_id = player.player_name, player.brawlhalla_player_id

        embed = build_featured_embed(
            player_name=player_name,
            note=note,
            site_url=self.bot.settings.site_url,
            brawlhalla_id=player_id,
        )
        if self.bot.settings.announce_featured:
            channel = await resolve_provisioned_channel(
                self.bot, staff.guild, CHANNEL_ANNOUNCEMENTS.logical_key
            )
            if channel is not None:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    logger.warning("Missing permission to announce the featured player")
        await interaction.followup.send(
            "Featured — the website picks it up on its next refresh.", embed=embed, ephemeral=True
        )

    @app_commands.command(name="sync", description="Re-sync the bot's slash commands (admin)")
    @require_setup_authorized()
    async def sync(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = discord.Object(id=self.bot.settings.guild_id)
        self.bot.tree.copy_global_to(guild=guild)
        synced = await self.bot.tree.sync(guild=guild)
        logger.info("/sync by %s: %d command(s)", interaction.user.id, len(synced))
        await interaction.followup.send(f"Synced {len(synced)} command(s).", ephemeral=True)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(StaffCog(bot))
