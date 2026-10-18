"""The opt-in Spar Ping role (docs/DECISIONS.md ADR-136).

Members tap 🔔 on the spar panel to get the role; every spar call then tags
it (at most once per services.spar_service.PING_COOLDOWN per guild). The role
is created on first use with no permissions and isn't hoisted. It's left
unmentionable when the bot can mention any role (Mention @everyone), so only
the bot can ping it; otherwise it has to be mentionable for the bot's ping
to land, which also lets members ping it by hand.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from database.session import session_scope
from services.spar_service import SparService

if TYPE_CHECKING:
    from bot.client import ShaheenBot

logger = logging.getLogger(__name__)

SPAR_ROLE_NAME = "Spar Ping"
_SPAR_ROLE_COLOUR = 0xFF6A1F


async def spar_role(bot: ShaheenBot, guild: discord.Guild) -> discord.Role | None:
    """The guild's Spar Ping role, if it exists."""
    async with session_scope(bot.session_factory) as session:
        role_id = await SparService(session).spar_role_id(guild.id)
    return guild.get_role(role_id) if role_id else None


async def ensure_spar_role(bot: ShaheenBot, guild: discord.Guild) -> discord.Role | None:
    """The Spar Ping role, created on first use. None if the bot can't manage roles."""
    role = await spar_role(bot, guild)
    if role is not None:
        return role
    me = guild.me
    if not me.guild_permissions.manage_roles:
        return None
    # Reuse a same-named role staff made by hand rather than duplicating it.
    role = discord.utils.get(guild.roles, name=SPAR_ROLE_NAME)
    if role is None:
        role = await guild.create_role(
            name=SPAR_ROLE_NAME,
            colour=discord.Colour(_SPAR_ROLE_COLOUR),
            permissions=discord.Permissions.none(),
            hoist=False,
            mentionable=not me.guild_permissions.mention_everyone,
            reason="BRAWLISTAN: opt-in spar pings",
        )
        logger.info("Created the Spar Ping role in guild %s", guild.id)
    async with session_scope(bot.session_factory) as session:
        await SparService(session).set_spar_role(guild.id, role.id)
    return role


async def toggle_spar_role(bot: ShaheenBot, member: discord.Member) -> bool | None:
    """Give or take the role. True if they now have it, None if it can't be managed."""
    role = await ensure_spar_role(bot, member.guild)
    if role is None or role >= member.guild.me.top_role:
        return None
    if role in member.roles:
        await member.remove_roles(role, reason="Turned spar pings off")
        return False
    await member.add_roles(role, reason="Turned spar pings on")
    return True


def spar_ping_message(state: bool | None) -> str:
    """The reply after toggling, from toggle_spar_role's result."""
    if state is None:
        return "⚠️ Spar pings aren't available: BRAWLISTAN can't manage that role. Ask staff."
    if state:
        return "🔔 Spar pings **on**: you'll be tagged when someone's looking for a game."
    return "🔕 Spar pings **off**. Tap 🔔 or use `/sparping` to turn them back on."
