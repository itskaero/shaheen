"""Reaction roles (docs/DECISIONS.md ADR-137): react to a message, get a role.

`/reactionrole post` puts up a branded panel; `/reactionrole add` binds an
emoji on any message (a panel or not) to a role and adds the bot's own
reaction so members only have to tap it. Panels the bot posted list their
emoji and roles and update themselves. Rules and storage live in
services/reaction_role_service.py; this is the Discord side.

Only safe roles can be handed out: not @everyone, not managed by an
integration, below both the bot's and the staff member's top role, and with
no moderation or admin permissions. The checks run again on every reaction,
so a role given a dangerous permission later stops being handed out.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import require_setup_authorized
from bot.client import ShaheenBot
from bot.palette import GOLD
from core.exceptions import ShaheenError
from database.models.reaction_role import ReactionRole
from database.session import session_scope
from services.reaction_role_service import (
    MessageRef,
    ReactionRoleService,
    normalize_emoji,
    parse_message_link,
)

logger = logging.getLogger(__name__)

# Permissions a self-assigned role must never carry.
DANGEROUS = discord.Permissions(
    administrator=True,
    manage_guild=True,
    manage_roles=True,
    manage_channels=True,
    manage_messages=True,
    manage_webhooks=True,
    manage_nicknames=True,
    manage_expressions=True,
    manage_events=True,
    manage_threads=True,
    kick_members=True,
    ban_members=True,
    moderate_members=True,
    mention_everyone=True,
    view_audit_log=True,
    move_members=True,
    mute_members=True,
    deafen_members=True,
)
PANEL_FOOTER = "BRAWLISTAN · react below to pick your roles"


def role_problem(role: discord.Role, *, bot_member: discord.Member) -> str | None:
    """Why the bot shouldn't hand this role out, or None if it's fine."""
    if role.is_default():
        return "@everyone can't be a reaction role."
    if role.managed:
        return f"{role.name} is managed by an integration or bot."
    if role.permissions.value & DANGEROUS.value:
        return f"{role.name} carries moderation or admin permissions; self-assign only plain roles."
    if role >= bot_member.top_role:
        return f"{role.name} is above my highest role; move my role above it."
    return None


def build_panel_embed(
    title: str, description: str | None, bindings: list[tuple[str, int]]
) -> discord.Embed:
    """A reaction-role panel: its intro, then one line per emoji and role."""
    lines = [description] if description else []
    if bindings:
        if lines:
            lines.append("")
        lines += [f"{emoji}  <@&{role_id}>" for emoji, role_id in bindings]
    else:
        lines.append("*Roles coming soon.*")
    embed = discord.Embed(title=title, description="\n".join(lines), colour=GOLD)
    embed.set_footer(text=PANEL_FOOTER)
    return embed


class ReactionRolesCog(commands.Cog):
    reactionrole = app_commands.Group(
        name="reactionrole", description="Roles members pick by reacting to a message"
    )

    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot
        # Messages with bindings, so unrelated reactions never touch the database.
        self._messages: set[int] = set()

    async def cog_load(self) -> None:
        async with session_scope(self.bot.session_factory) as session:
            self._messages = await ReactionRoleService(session).message_ids()

    # --- reactions -------------------------------------------------------------

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.message_id in self._messages and payload.member is not None:
            await self._apply(payload, payload.member, add=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.message_id not in self._messages or payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id) if guild else None
        if member is not None:
            await self._apply(payload, member, add=False)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if payload.message_id in self._messages:
            async with session_scope(self.bot.session_factory) as session:
                await ReactionRoleService(session).forget_message(payload.message_id)
            self._messages.discard(payload.message_id)

    async def _apply(
        self, payload: discord.RawReactionActionEvent, member: discord.Member, *, add: bool
    ) -> None:
        if member.bot or payload.guild_id is None:
            return
        async with session_scope(self.bot.session_factory) as session:
            role_id = await ReactionRoleService(session).role_for(
                payload.guild_id, payload.message_id, str(payload.emoji)
            )
        role = member.guild.get_role(role_id) if role_id else None
        if role is None:
            return
        problem = role_problem(role, bot_member=member.guild.me)
        if problem:
            logger.warning("Reaction role %s not applied: %s", role.id, problem)
            return
        try:
            if add and role not in member.roles:
                await member.add_roles(role, reason="Reaction role")
            elif not add and role in member.roles:
                await member.remove_roles(role, reason="Reaction role removed")
        except discord.HTTPException as exc:
            logger.warning("Reaction role %s for member %s failed: %s", role.id, member.id, exc)

    # --- commands --------------------------------------------------------------

    @reactionrole.command(name="post", description="Post a reaction-role panel (admin)")
    @app_commands.describe(
        channel="Where to post it",
        title="Panel title, e.g. 'Pick your region'",
        description="Optional intro line above the roles",
    )
    @require_setup_authorized()
    async def post(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: app_commands.Range[str, 1, 100],
        description: app_commands.Range[str, 1, 1000] | None = None,
    ) -> None:
        guild = _guild(interaction)
        perms = channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.embed_links and perms.add_reactions):
            raise ShaheenError(
                f"I need Send Messages, Embed Links and Add Reactions in {channel.mention}."
            )
        message = await channel.send(embed=build_panel_embed(title, description, []))
        await interaction.response.send_message(
            f"Panel posted: {message.jump_url}\nNow add roles to it with `/reactionrole add`, "
            "pasting that link as `message`.",
            ephemeral=True,
        )

    @reactionrole.command(name="add", description="Give a role to whoever reacts with an emoji")
    @app_commands.describe(
        message="Link to the message (right-click it → Copy Message Link)",
        emoji="The emoji to react with (a standard one or one of this server's)",
        role="The role to give",
    )
    @require_setup_authorized()
    async def add(
        self, interaction: discord.Interaction, message: str, emoji: str, role: discord.Role
    ) -> None:
        guild = _guild(interaction)
        ref = _message_ref(guild, message)
        normalized = normalize_emoji(emoji)
        if normalized is None:
            raise ShaheenError("That isn't an emoji. Pick one from the emoji picker.")
        problem = role_problem(role, bot_member=guild.me)
        if problem:
            raise ShaheenError(problem)
        actor = interaction.user
        if (
            isinstance(actor, discord.Member)
            and actor.id != guild.owner_id
            and role >= actor.top_role
        ):
            raise ShaheenError(f"{role.name} is above your highest role.")
        await interaction.response.defer(ephemeral=True)
        target = await _fetch_message(guild, ref)
        try:
            await target.add_reaction(normalized)
        except discord.HTTPException as exc:
            raise ShaheenError(
                "I couldn't react with that emoji there. Use a standard emoji or one from this "
                "server, and check I have Add Reactions and Read Message History."
            ) from exc
        async with session_scope(self.bot.session_factory) as session:
            await ReactionRoleService(session).add(
                message=ref, emoji=normalized, role_id=role.id, actor_discord_id=actor.id
            )
        self._messages.add(ref.message_id)
        await self._refresh_panel(target)
        await interaction.followup.send(
            f"Done: reacting {normalized} on {target.jump_url} gives **{role.name}**.",
            ephemeral=True,
        )

    @reactionrole.command(name="remove", description="Stop an emoji giving a role (admin)")
    @app_commands.describe(message="Link to the message", emoji="The emoji to remove")
    @require_setup_authorized()
    async def remove(self, interaction: discord.Interaction, message: str, emoji: str) -> None:
        guild = _guild(interaction)
        ref = _message_ref(guild, message)
        normalized = normalize_emoji(emoji)
        if normalized is None:
            raise ShaheenError("That isn't an emoji.")
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = ReactionRoleService(session)
            binding = await service.remove(
                guild_id=guild.id,
                message_id=ref.message_id,
                emoji=normalized,
                actor_discord_id=interaction.user.id,
            )
            if not await service.for_message(ref.message_id):
                self._messages.discard(ref.message_id)
        try:
            target = await _fetch_message(guild, ref)
            await target.remove_reaction(binding.emoji, guild.me)
            await self._refresh_panel(target)
        except (ShaheenError, discord.HTTPException):
            pass  # the binding is gone either way
        await interaction.followup.send(
            f"{normalized} no longer gives a role there. "
            "Members who already have the role keep it.",
            ephemeral=True,
        )

    @reactionrole.command(name="list", description="Every reaction role in the server (admin)")
    @require_setup_authorized()
    async def list_roles(self, interaction: discord.Interaction) -> None:
        guild = _guild(interaction)
        async with session_scope(self.bot.session_factory) as session:
            bindings = await ReactionRoleService(session).for_guild(guild.id)
        await interaction.response.send_message(
            embed=build_list_embed(guild.id, bindings), ephemeral=True
        )

    async def _refresh_panel(self, message: discord.Message) -> None:
        """Rewrite a bot-posted panel's role list from the stored bindings."""
        if self.bot.user is None or message.author.id != self.bot.user.id:
            return
        embed = message.embeds[0] if message.embeds else None
        if embed is None or embed.footer.text != PANEL_FOOTER:
            return
        async with session_scope(self.bot.session_factory) as session:
            bindings = await ReactionRoleService(session).for_message(message.id)
        intro = _panel_intro(embed.description or "")
        await message.edit(
            embed=build_panel_embed(
                embed.title or "Pick your roles", intro, [(b.emoji, b.role_id) for b in bindings]
            )
        )


def build_list_embed(guild_id: int, bindings: list[ReactionRole]) -> discord.Embed:
    embed = discord.Embed(title="Reaction roles", colour=GOLD)
    if not bindings:
        embed.description = "None yet. Start with `/reactionrole post` or `/reactionrole add`."
        return embed
    by_message: dict[tuple[int, int], list[str]] = {}
    for b in bindings:
        by_message.setdefault((b.channel_id, b.message_id), []).append(f"{b.emoji} <@&{b.role_id}>")
    lines = [
        f"[Message](https://discord.com/channels/{guild_id}/{channel_id}/{message_id}): "
        + ", ".join(items)
        for (channel_id, message_id), items in by_message.items()
    ]
    embed.description = "\n".join(lines)[:4000]
    return embed


def _panel_intro(description: str) -> str | None:
    """A panel's intro: everything before its role lines."""
    intro: list[str] = []
    for line in description.split("\n"):
        if "<@&" in line or line == "*Roles coming soon.*":
            break
        intro.append(line)
    return "\n".join(intro).strip() or None


def _guild(interaction: discord.Interaction) -> discord.Guild:
    if interaction.guild is None:
        raise ShaheenError("This only works inside the BRAWLISTAN server.")
    return interaction.guild


def _message_ref(guild: discord.Guild, link: str) -> MessageRef:
    ref = parse_message_link(link)
    if ref is None:
        raise ShaheenError("Paste a message link: right-click the message → Copy Message Link.")
    if ref.guild_id != guild.id:
        raise ShaheenError("That message is in another server.")
    return ref


async def _fetch_message(guild: discord.Guild, ref: MessageRef) -> discord.Message:
    channel = guild.get_channel_or_thread(ref.channel_id)
    if not isinstance(channel, discord.TextChannel | discord.Thread):
        raise ShaheenError("I can't see that channel.")
    try:
        return await channel.fetch_message(ref.message_id)
    except discord.HTTPException as exc:
        raise ShaheenError("I can't find that message (deleted, or I can't read it).") from exc


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(ReactionRolesCog(bot))
