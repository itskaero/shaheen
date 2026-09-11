"""Branded embeds for bot/cogs/moderation.py (docs/DECISIONS.md ADR-065).

Two shared, parameterized builders (`build_mod_confirm_embed`/
`build_mod_log_embed`) cover /kick, /ban, /timeout, /purge, and
/clearwarnings — they're all structurally the same "confirm this
destructive action" / "log what happened" shape. /warn gets its own
functions since it has a genuinely different audience (a DM to the warned
member) and shape (a running warning count).
"""

from __future__ import annotations

import discord

from bot.palette import GOLD

_DANGER = 0xB00020


def build_mod_confirm_embed(
    *, action: str, target: discord.abc.User, detail: str | None = None
) -> discord.Embed:
    description = f"Are you sure you want to **{action.lower()}** {target.mention}?"
    if detail:
        description += f"\n{detail}"
    return discord.Embed(title=f"⚠️ Confirm {action}", description=description, colour=_DANGER)


def build_mod_log_embed(
    *,
    action: str,
    target: discord.abc.User,
    moderator: discord.abc.User,
    reason: str | None = None,
    detail: str | None = None,
) -> discord.Embed:
    description = (
        f"**Target:** {target.mention} (`{target.id}`)\n**Moderator:** {moderator.mention}"
    )
    if reason:
        description += f"\n**Reason:** {reason}"
    if detail:
        description += f"\n{detail}"
    return discord.Embed(title=f"🛡️ {action}", description=description, colour=GOLD)


def build_warn_dm_embed(*, guild_name: str, reason: str) -> discord.Embed:
    return discord.Embed(
        title=f"⚠️ You were warned in {guild_name}",
        description=f"**Reason:** {reason}\n\nRepeated warnings can lead to further action.",
        colour=_DANGER,
    )


def build_warn_confirmation_embed(*, target: discord.abc.User, active_count: int) -> discord.Embed:
    return discord.Embed(
        title="✅ Warning Issued",
        description=f"{target.mention} now has **{active_count}** active warning(s).",
        colour=GOLD,
    )


def build_warnings_embed(
    *, target: discord.abc.User, warnings: list[tuple[str, int, str]]
) -> discord.Embed:
    """`warnings` is (reason, moderator_discord_id, timestamp_str) tuples,
    newest first — kept as plain tuples rather than importing the Warning
    ORM model here, matching bot/content's Discord-facing-only role
    (docs/ARCHITECTURE.md).
    """
    embed = discord.Embed(title=f"🛡️ Active Warnings — {target.display_name}", colour=GOLD)
    if not warnings:
        embed.description = "No active warnings."
        return embed
    lines = [
        f"**{i}.** {reason} — <@{mod_id}> ({timestamp})"
        for i, (reason, mod_id, timestamp) in enumerate(warnings, start=1)
    ]
    embed.description = "\n".join(lines[:20])
    if len(warnings) > 20:
        embed.set_footer(text=f"...and {len(warnings) - 20} more.")
    return embed


def build_clearwarnings_log_embed(
    *, target: discord.abc.User, moderator: discord.abc.User, count: int
) -> discord.Embed:
    return build_mod_log_embed(
        action="Warnings Cleared",
        target=target,
        moderator=moderator,
        detail=f"**Cleared:** {count} warning(s)",
    )


def build_purge_log_embed(
    *,
    moderator: discord.abc.User,
    channel: discord.TextChannel,
    count: int,
    target: discord.abc.User | None,
) -> discord.Embed:
    detail = f"**Channel:** {channel.mention}\n**Messages deleted:** {count}"
    if target:
        detail += f"\n**Filtered to:** {target.mention}"
    return discord.Embed(
        title="🛡️ Messages Purged",
        description=f"**Moderator:** {moderator.mention}\n{detail}",
        colour=GOLD,
    )
