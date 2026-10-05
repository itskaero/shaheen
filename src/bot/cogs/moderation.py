"""Moderation commands (docs/DECISIONS.md ADR-065).

Stays thin (docs/ARCHITECTURE.md): embed formatting lives in
bot/content/moderation_embeds.py, warning persistence in
database/repositories/warning_repository.py. Discord's own kick/timeout/
purge/voice-mute permissions are already granted to ROLE_MODERATOR
natively (bot/constants.py) — these commands add slash-command
discoverability, a confirmation step, and a #mod-log audit trail on top of
what Discord's own UI already lets a Moderator do; /warn/-warnings/
-clearwarnings add something genuinely new (a structured, bot-tracked
warning record — nothing native does this).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt

from bot.checks.permissions import require_staff_authorized
from bot.client import ShaheenBot
from bot.cogs.competition import resolve_provisioned_channel
from bot.constants import CHANNEL_REPORT
from bot.content.moderation_embeds import (
    build_clearwarnings_log_embed,
    build_lock_log_embed,
    build_mod_confirm_embed,
    build_mod_log_embed,
    build_nickname_log_embed,
    build_purge_log_embed,
    build_slowmode_log_embed,
    build_unban_log_embed,
    build_unlock_log_embed,
    build_untimeout_log_embed,
    build_warn_confirmation_embed,
    build_warn_dm_embed,
    build_warnings_embed,
)
from bot.content.network_embeds import build_player_report_embed, build_report_received_embed
from bot.views.confirm import ConfirmView
from core.exceptions import ShaheenError
from database.models.player_report import PlayerReport
from database.repositories.warning_repository import WarningRepository
from database.session import session_scope
from services.report_service import ReportService

logger = logging.getLogger(__name__)

# Moderation actions are logged to MOD_LOG_CHANNEL_ID if set, else to
# #report (ADR-109; the old #mod-log channel retired).


def _require_member(interaction: discord.Interaction) -> discord.Member:
    member = interaction.user
    if not isinstance(member, discord.Member) or interaction.guild is None:
        raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
    return member


async def post_player_report(
    bot: ShaheenBot, guild: discord.Guild, report: PlayerReport, *, reporter: str | None
) -> int | None:
    """Post a report's card to #report (or REPORT_CHANNEL_ID); the message id,
    or None when there's nowhere to post (ADR-111). Mentions in the card never
    ping anyone."""
    channel = await resolve_provisioned_channel(bot, guild, CHANNEL_REPORT.logical_key)
    if channel is None:
        logger.warning("Report #%s not posted: no #report channel", report.id)
        return None
    try:
        message = await channel.send(
            embed=build_player_report_embed(report, reporter=reporter),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.HTTPException as exc:
        logger.warning("Report #%s not posted: %s", report.id, exc)
        return None
    return message.id


class ModerationCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    async def _log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel: discord.abc.GuildChannel | None = None
        if self.bot.settings.mod_log_channel_id is not None:
            channel = guild.get_channel(self.bot.settings.mod_log_channel_id)
        if not isinstance(channel, discord.TextChannel):
            channel = await resolve_provisioned_channel(self.bot, guild, CHANNEL_REPORT.logical_key)
        if channel is None:
            logger.warning("No mod-log channel — run /setup run or set MOD_LOG_CHANNEL_ID")
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Missing permission to post in the mod-log channel")

    # --- /report (players; ADR-111) -----------------------------------------

    @app_commands.command(name="report", description="Privately report a player to staff")
    @app_commands.describe(
        player="The member you're reporting",
        name="Or their Brawlhalla name, if they're not in the server",
        reason="What happened (at least 10 characters)",
    )
    async def report(
        self,
        interaction: discord.Interaction,
        reason: app_commands.Range[str, 1, 1000],
        player: discord.Member | None = None,
        name: app_commands.Range[str, 1, 64] | None = None,
    ) -> None:
        reporter = _require_member(interaction)
        if player is None and not name:
            raise ShaheenError("Pick the member you're reporting, or give their name.")
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = ReportService(session)
            report = await service.create(
                guild_id=reporter.guild.id,
                source="discord",
                reporter_discord_id=reporter.id,
                reported_discord_id=player.id if player else None,
                reported_name=player.display_name if player else (name or ""),
                reason=reason,
            )
            message_id = await post_player_report(
                self.bot, reporter.guild, report, reporter=reporter.mention
            )
            if message_id is not None:
                await service.mark_posted(report, message_id)
            report_id = report.id
        await interaction.followup.send(
            embed=build_report_received_embed(report_id), ephemeral=True
        )

    # --- /warn / /warnings / /clearwarnings --------------------------------

    @app_commands.command(name="warn", description="Issue a warning to a member (staff only)")
    @app_commands.describe(user="Who to warn", reason="Why they're being warned")
    @require_staff_authorized()
    async def warn(
        self, interaction: discord.Interaction, user: discord.Member, reason: str
    ) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            await WarningRepository(session).add(
                guild_id=moderator.guild.id,
                discord_id=user.id,
                moderator_discord_id=moderator.id,
                reason=reason,
            )
            active_count = await WarningRepository(session).count_active_for_member(
                guild_id=moderator.guild.id, discord_id=user.id
            )

        dm_embed = build_warn_dm_embed(guild_name=moderator.guild.name, reason=reason)
        with contextlib.suppress(discord.Forbidden):
            # DMs closed — the warning still counts, just wasn't delivered privately
            await user.send(embed=dm_embed)

        await self._log(
            moderator.guild,
            build_mod_log_embed(
                action="Warning Issued",
                target=user,
                moderator=moderator,
                reason=reason,
                detail=f"**Active warnings:** {active_count}",
            ),
        )
        await interaction.followup.send(
            embed=build_warn_confirmation_embed(target=user, active_count=active_count),
            ephemeral=True,
        )

    @app_commands.command(
        name="warnings", description="List a member's active warnings (staff only)"
    )
    @app_commands.describe(user="Whose warnings to show")
    @require_staff_authorized()
    async def warnings(self, interaction: discord.Interaction, user: discord.Member) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            rows = await WarningRepository(session).list_active_for_member(
                guild_id=moderator.guild.id, discord_id=user.id
            )

        entries = [
            (w.reason, w.moderator_discord_id, format_dt(w.created_at, style="R")) for w in rows
        ]
        await interaction.followup.send(
            embed=build_warnings_embed(target=user, warnings=entries), ephemeral=True
        )

    @app_commands.command(
        name="clearwarnings", description="Clear all of a member's active warnings (staff only)"
    )
    @app_commands.describe(user="Whose warnings to clear")
    @require_staff_authorized()
    async def clearwarnings(self, interaction: discord.Interaction, user: discord.Member) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            active_count = await WarningRepository(session).count_active_for_member(
                guild_id=moderator.guild.id, discord_id=user.id
            )
        if active_count == 0:
            await interaction.followup.send(
                f"{user.mention} has no active warnings.", ephemeral=True
            )
            return

        view = ConfirmView(author_id=moderator.id)
        message = await interaction.followup.send(
            embed=build_mod_confirm_embed(
                action="Clear Warnings",
                target=user,
                detail=f"This clears **{active_count}** active warning(s).",
            ),
            view=view,
            ephemeral=True,
            wait=True,
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Cancelled.", embed=None, view=None)
            return

        async with session_scope(self.bot.session_factory) as session:
            cleared = await WarningRepository(session).clear_all_for_member(
                guild_id=moderator.guild.id, discord_id=user.id
            )

        await self._log(
            moderator.guild,
            build_clearwarnings_log_embed(target=user, moderator=moderator, count=cleared),
        )
        await message.edit(
            content=f"Cleared {cleared} warning(s) for {user.mention}.", embed=None, view=None
        )

    # --- /kick / /ban / /timeout --------------------------------------------

    async def _confirm(
        self, interaction: discord.Interaction, *, action: str, target: discord.Member, detail: str
    ) -> discord.WebhookMessage | None:
        """Shows a Confirm/Cancel view for a destructive action. Returns
        the sent message to keep editing if confirmed, or None (already
        edited to "Cancelled") if the moderator backed out.
        """
        moderator = _require_member(interaction)
        view = ConfirmView(author_id=moderator.id)
        message = await interaction.followup.send(
            embed=build_mod_confirm_embed(action=action, target=target, detail=detail),
            view=view,
            ephemeral=True,
            wait=True,
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Cancelled.", embed=None, view=None)
            return None
        return message

    @app_commands.command(name="kick", description="Kick a member (staff only)")
    @app_commands.describe(user="Who to kick", reason="Why they're being kicked")
    @require_staff_authorized()
    async def kick(
        self, interaction: discord.Interaction, user: discord.Member, reason: str
    ) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        message = await self._confirm(
            interaction, action="Kick", target=user, detail=f"**Reason:** {reason}"
        )
        if message is None:
            return

        try:
            await user.kick(reason=reason)
        except discord.Forbidden:
            await message.edit(
                content="⚠️ I don't have permission to kick that member.", embed=None, view=None
            )
            return

        log_embed = build_mod_log_embed(
            action="Member Kicked", target=user, moderator=moderator, reason=reason
        )
        await self._log(moderator.guild, log_embed)
        await message.edit(content=f"{user.mention} was kicked.", embed=None, view=None)

    @app_commands.command(name="ban", description="Ban a member (staff only)")
    @app_commands.describe(
        user="Who to ban",
        reason="Why they're being banned",
        delete_message_days="Days of their message history to delete (0-7, default 0)",
    )
    @require_staff_authorized()
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
        delete_message_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        message = await self._confirm(
            interaction, action="Ban", target=user, detail=f"**Reason:** {reason}"
        )
        if message is None:
            return

        try:
            await user.ban(reason=reason, delete_message_days=delete_message_days)
        except discord.Forbidden:
            await message.edit(
                content="⚠️ I don't have permission to ban that member.", embed=None, view=None
            )
            return

        log_embed = build_mod_log_embed(
            action="Member Banned", target=user, moderator=moderator, reason=reason
        )
        await self._log(moderator.guild, log_embed)
        await message.edit(content=f"{user.mention} was banned.", embed=None, view=None)

    @app_commands.command(name="timeout", description="Timeout a member (staff only)")
    @app_commands.describe(
        user="Who to timeout",
        minutes="Timeout duration in minutes (max 40320 / 28 days)",
        reason="Why they're being timed out",
    )
    @require_staff_authorized()
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str,
    ) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        try:
            await user.timeout(dt.timedelta(minutes=minutes), reason=reason)
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to timeout that member.", ephemeral=True
            )
            return

        await self._log(
            moderator.guild,
            build_mod_log_embed(
                action="Member Timed Out",
                target=user,
                moderator=moderator,
                reason=reason,
                detail=f"**Duration:** {minutes} minute(s)",
            ),
        )
        await interaction.followup.send(
            f"{user.mention} timed out for {minutes} minute(s).", ephemeral=True
        )

    # --- /clear (was /purge until ADR-111) ------------------------------------

    @app_commands.command(
        name="clear", description="Delete recent messages in this channel (staff only)"
    )
    @app_commands.describe(
        amount="How many messages to delete (1-100)", user="Only delete this user's messages"
    )
    @require_staff_authorized()
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
        user: discord.Member | None = None,
    ) -> None:
        moderator = _require_member(interaction)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            raise ShaheenError("This command can only be used in a text channel.")

        await interaction.response.defer(ephemeral=True)

        def _check(message: discord.Message) -> bool:
            return user is None or message.author.id == user.id

        try:
            deleted = await channel.purge(limit=amount, check=_check)
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to delete messages here.", ephemeral=True
            )
            return

        purge_embed = build_purge_log_embed(
            moderator=moderator, channel=channel, count=len(deleted), target=user
        )
        await self._log(moderator.guild, purge_embed)
        await interaction.followup.send(f"Deleted {len(deleted)} message(s).", ephemeral=True)

    # --- /unban / /untimeout ------------------------------------------------

    @app_commands.command(name="unban", description="Remove a ban (staff only)")
    @app_commands.describe(user="Who to unban", reason="Why they're being unbanned")
    @require_staff_authorized()
    async def unban(
        self, interaction: discord.Interaction, user: discord.User, reason: str | None = None
    ) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        try:
            await moderator.guild.unban(user, reason=reason)
        except discord.NotFound:
            await interaction.followup.send(f"{user.mention} isn't banned.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("⚠️ I don't have permission to unban.", ephemeral=True)
            return

        await self._log(
            moderator.guild,
            build_unban_log_embed(target=user, moderator=moderator, reason=reason),
        )
        await interaction.followup.send(f"{user.mention} was unbanned.", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove an active timeout (staff only)")
    @app_commands.describe(user="Who to remove the timeout from", reason="Why")
    @require_staff_authorized()
    async def untimeout(
        self, interaction: discord.Interaction, user: discord.Member, reason: str | None = None
    ) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        try:
            await user.timeout(None, reason=reason)
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to untimeout that member.", ephemeral=True
            )
            return

        await self._log(
            moderator.guild,
            build_untimeout_log_embed(target=user, moderator=moderator, reason=reason),
        )
        await interaction.followup.send(f"Timeout removed for {user.mention}.", ephemeral=True)

    # --- /lock / /unlock / /slowmode ----------------------------------------

    @staticmethod
    def _resolve_text_channel(
        interaction: discord.Interaction, channel: discord.TextChannel | None
    ) -> discord.TextChannel:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            raise ShaheenError("This command can only target a text channel.")
        return target

    @app_commands.command(
        name="lock", description="Stop @everyone from sending in a channel (staff only)"
    )
    @app_commands.describe(
        channel="Channel to lock (defaults to this one)", reason="Why it's being locked"
    )
    @require_staff_authorized()
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        reason: str | None = None,
    ) -> None:
        moderator = _require_member(interaction)
        target_channel = self._resolve_text_channel(interaction, channel)
        await interaction.response.defer(ephemeral=True)

        overwrite = target_channel.overwrites_for(moderator.guild.default_role)
        overwrite.update(send_messages=False)
        try:
            await target_channel.set_permissions(
                moderator.guild.default_role, overwrite=overwrite, reason=reason
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to edit that channel.", ephemeral=True
            )
            return

        await self._log(
            moderator.guild,
            build_lock_log_embed(channel=target_channel, moderator=moderator, reason=reason),
        )
        await interaction.followup.send(f"🔒 {target_channel.mention} locked.", ephemeral=True)

    @app_commands.command(name="unlock", description="Undo a /lock on a channel (staff only)")
    @app_commands.describe(channel="Channel to unlock (defaults to this one)")
    @require_staff_authorized()
    async def unlock(
        self, interaction: discord.Interaction, channel: discord.TextChannel | None = None
    ) -> None:
        moderator = _require_member(interaction)
        target_channel = self._resolve_text_channel(interaction, channel)
        await interaction.response.defer(ephemeral=True)

        default_role = moderator.guild.default_role
        overwrite = target_channel.overwrites_for(default_role)
        overwrite.update(send_messages=None)
        try:
            if overwrite.is_empty():
                await target_channel.set_permissions(
                    default_role, overwrite=None, reason="Shaheen /unlock"
                )
            else:
                await target_channel.set_permissions(
                    default_role, overwrite=overwrite, reason="Shaheen /unlock"
                )
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to edit that channel.", ephemeral=True
            )
            return

        await self._log(
            moderator.guild, build_unlock_log_embed(channel=target_channel, moderator=moderator)
        )
        await interaction.followup.send(f"🔓 {target_channel.mention} unlocked.", ephemeral=True)

    @app_commands.command(
        name="slowmode", description="Set this channel's slowmode delay (staff only)"
    )
    @app_commands.describe(
        seconds="Delay between messages, in seconds (0 disables it)",
        channel="Channel to update (defaults to this one)",
    )
    @require_staff_authorized()
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
        channel: discord.TextChannel | None = None,
    ) -> None:
        moderator = _require_member(interaction)
        target_channel = self._resolve_text_channel(interaction, channel)
        await interaction.response.defer(ephemeral=True)

        try:
            await target_channel.edit(slowmode_delay=seconds, reason="Shaheen /slowmode")
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to edit that channel.", ephemeral=True
            )
            return

        await self._log(
            moderator.guild,
            build_slowmode_log_embed(channel=target_channel, moderator=moderator, seconds=seconds),
        )
        detail = "disabled" if seconds == 0 else f"set to {seconds}s"
        await interaction.followup.send(
            f"🐢 Slowmode {detail} in {target_channel.mention}.", ephemeral=True
        )

    # --- /nickname -----------------------------------------------------------

    @app_commands.command(
        name="nickname", description="Set or reset a member's nickname (staff only)"
    )
    @app_commands.describe(
        user="Whose nickname to change",
        nickname="New nickname (omit to reset to their username)",
        reason="Why",
    )
    @require_staff_authorized()
    async def nickname(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nickname: str | None = None,
        reason: str | None = None,
    ) -> None:
        moderator = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)
        old_nick = user.display_name

        try:
            await user.edit(nick=nickname, reason=reason)
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to rename that member.", ephemeral=True
            )
            return

        await self._log(
            moderator.guild,
            build_nickname_log_embed(
                target=user,
                moderator=moderator,
                old_nick=old_nick,
                new_nick=nickname,
                reason=reason,
            ),
        )
        await interaction.followup.send(f"Nickname updated for {user.mention}.", ephemeral=True)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(ModerationCog(bot))
