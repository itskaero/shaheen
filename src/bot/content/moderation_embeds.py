"""Branded embeds for bot/cogs/moderation.py (docs/DECISIONS.md ADR-065,
ADR-090 for the visual pass).

Two shared, parameterized builders (`build_mod_confirm_embed`/
`build_mod_log_embed`) cover /kick, /ban, /timeout, /unban, /untimeout,
/lock, /unlock, /slowmode, /nickname, /purge, and /clearwarnings — they're
all structurally the same "confirm this destructive action" / "log what
happened" shape. /warn gets its own functions since it has a genuinely
different audience (a DM to the warned member) and shape (a running
warning count).

Every log/confirm embed carries the target's avatar as a thumbnail and,
where a moderator is attached, their name and avatar in the footer plus a
timestamp — small things, but a wall of identical grey text in #mod-log is
hard to scan at 2am; a face and a "who, when" makes it skimmable.
"""

from __future__ import annotations

import discord

from bot.palette import EMERALD, GOLD

_DANGER = 0xB00020


def _with_target_thumbnail(embed: discord.Embed, target: discord.abc.User) -> discord.Embed:
    avatar = getattr(target, "display_avatar", None)
    if avatar is not None:
        embed.set_thumbnail(url=avatar.url)
    return embed


def _with_moderator_footer(embed: discord.Embed, moderator: discord.abc.User) -> discord.Embed:
    avatar = getattr(moderator, "display_avatar", None)
    embed.set_footer(
        text=f"Actioned by {moderator}", icon_url=avatar.url if avatar is not None else None
    )
    embed.timestamp = discord.utils.utcnow()
    return embed


def build_mod_confirm_embed(
    *, action: str, target: discord.abc.User, detail: str | None = None
) -> discord.Embed:
    description = f"Are you sure you want to **{action.lower()}** {target.mention}?"
    if detail:
        description += f"\n{detail}"
    embed = discord.Embed(title=f"⚠️ Confirm {action}", description=description, colour=_DANGER)
    return _with_target_thumbnail(embed, target)


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
    embed = discord.Embed(title=f"🛡️ {action}", description=description, colour=GOLD)
    _with_target_thumbnail(embed, target)
    return _with_moderator_footer(embed, moderator)


def build_warn_dm_embed(*, guild_name: str, reason: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"⚠️ You were warned in {guild_name}",
        description=f"**Reason:** {reason}\n\nRepeated warnings can lead to further action.",
        colour=_DANGER,
    )
    embed.set_footer(text=guild_name)
    embed.timestamp = discord.utils.utcnow()
    return embed


def build_warn_confirmation_embed(*, target: discord.abc.User, active_count: int) -> discord.Embed:
    embed = discord.Embed(
        title="✅ Warning Issued",
        description=f"{target.mention} now has **{active_count}** active warning(s).",
        colour=GOLD,
    )
    return _with_target_thumbnail(embed, target)


def build_warnings_embed(
    *, target: discord.abc.User, warnings: list[tuple[str, int, str]]
) -> discord.Embed:
    """`warnings` is (reason, moderator_discord_id, timestamp_str) tuples,
    newest first — kept as plain tuples rather than importing the Warning
    ORM model here, matching bot/content's Discord-facing-only role
    (docs/ARCHITECTURE.md).
    """
    embed = discord.Embed(title=f"🛡️ Active Warnings — {target.display_name}", colour=GOLD)
    _with_target_thumbnail(embed, target)
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


def build_verify_success_embed(*, target: discord.abc.User) -> discord.Embed:
    embed = discord.Embed(
        title="✅ Member Verified",
        description=(
            f"{target.mention} now has community access. This is general access, not clan "
            f"roster membership — that comes from an approved `/apply`."
        ),
        colour=GOLD,
    )
    return _with_target_thumbnail(embed, target)


def build_already_verified_embed(*, target: discord.abc.User) -> discord.Embed:
    embed = discord.Embed(
        title="Already Verified",
        description=f"{target.mention} already holds a rank role above Guest — nothing to do.",
        colour=GOLD,
    )
    return _with_target_thumbnail(embed, target)


def build_verify_dm_embed(*, guild_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"✅ You're verified in {guild_name}!",
        description=(
            "A staff member gave you community access — welcome in! This isn't clan roster "
            "membership; run `/apply` if you want to try out for the roster."
        ),
        colour=GOLD,
    )
    embed.set_footer(text=guild_name)
    return embed


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
    embed = discord.Embed(
        title="🛡️ Messages Purged",
        description=f"**Moderator:** {moderator.mention}\n{detail}",
        colour=GOLD,
    )
    if target is not None:
        _with_target_thumbnail(embed, target)
    return _with_moderator_footer(embed, moderator)


# --- /unban / /untimeout ------------------------------------------------


def build_unban_log_embed(
    *, target: discord.abc.User, moderator: discord.abc.User, reason: str | None
) -> discord.Embed:
    return build_mod_log_embed(
        action="Member Unbanned", target=target, moderator=moderator, reason=reason
    )


def build_untimeout_log_embed(
    *, target: discord.abc.User, moderator: discord.abc.User, reason: str | None
) -> discord.Embed:
    return build_mod_log_embed(
        action="Timeout Removed", target=target, moderator=moderator, reason=reason
    )


# --- /lock / /unlock / /slowmode ----------------------------------------


def build_lock_log_embed(
    *, channel: discord.TextChannel, moderator: discord.abc.User, reason: str | None
) -> discord.Embed:
    description = f"**Channel:** {channel.mention}\n**Moderator:** {moderator.mention}"
    if reason:
        description += f"\n**Reason:** {reason}"
    embed = discord.Embed(title="🔒 Channel Locked", description=description, colour=_DANGER)
    return _with_moderator_footer(embed, moderator)


def build_unlock_log_embed(
    *, channel: discord.TextChannel, moderator: discord.abc.User
) -> discord.Embed:
    embed = discord.Embed(
        title="🔓 Channel Unlocked",
        description=f"**Channel:** {channel.mention}\n**Moderator:** {moderator.mention}",
        colour=EMERALD,
    )
    return _with_moderator_footer(embed, moderator)


def build_slowmode_log_embed(
    *, channel: discord.TextChannel, moderator: discord.abc.User, seconds: int
) -> discord.Embed:
    detail = "Slowmode disabled." if seconds == 0 else f"**Delay:** {seconds}s between messages."
    embed = discord.Embed(
        title="🐢 Slowmode Updated",
        description=f"**Channel:** {channel.mention}\n**Moderator:** {moderator.mention}\n{detail}",
        colour=GOLD,
    )
    return _with_moderator_footer(embed, moderator)


# --- /nickname -------------------------------------------------------------


def build_nickname_log_embed(
    *,
    target: discord.abc.User,
    moderator: discord.abc.User,
    old_nick: str | None,
    new_nick: str | None,
    reason: str | None,
) -> discord.Embed:
    detail = f"**Before:** {old_nick or '*(none)*'}\n**After:** {new_nick or '*(reset)*'}"
    return build_mod_log_embed(
        action="Nickname Changed",
        target=target,
        moderator=moderator,
        reason=reason,
        detail=detail,
    )
