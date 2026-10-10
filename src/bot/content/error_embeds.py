"""The staff copy of an unexpected command error (docs/DECISIONS.md ADR-126).

The member sees a short reference; staff get the same reference, the command
and the error's type and first line in the mod-log channel, so a failure can
be diagnosed from Discord without reading the server logs. The text goes
through core.logging.redact, and the channel is staff-only (ADR-109).
"""

from __future__ import annotations

import secrets

import discord

from bot.palette import GREY
from core.logging import redact

_DETAIL_LIMIT = 300


def error_reference() -> str:
    """A short id shared by the member's message, the staff post and the log."""
    return secrets.token_hex(3)


def describe_error(error: BaseException) -> str:
    """`Type: first line`, redacted and trimmed — never the full traceback."""
    first_line = (str(error).strip().splitlines() or [""])[0]
    text = f"{type(error).__name__}: {first_line}" if first_line else type(error).__name__
    text = redact(text)
    return text if len(text) <= _DETAIL_LIMIT else text[: _DETAIL_LIMIT - 1] + "…"


def build_error_report_embed(
    *, command: str, reference: str, error: BaseException, user_id: int | None
) -> discord.Embed:
    embed = discord.Embed(
        title=f"⚠️ Command error · {reference}",
        description=f"```{describe_error(error)}```",
        colour=GREY,
    )
    embed.add_field(name="Command", value=f"`/{command}`", inline=True)
    if user_id is not None:
        embed.add_field(name="Member", value=f"<@{user_id}>", inline=True)
    embed.set_footer(text=f"Full traceback in the bot logs: search for {reference}")
    return embed
