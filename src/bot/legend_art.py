"""Attach a rendered Legend portrait strip to an embed (docs/DECISIONS.md ADR-098)."""

from __future__ import annotations

import asyncio
import io
import logging
from collections.abc import Sequence

import discord

from services.legend_art import render_legend_strip

logger = logging.getLogger(__name__)

_FILENAME = "legends.png"


async def attach_legend_strip(
    embed: discord.Embed, legend_name_keys: Sequence[str]
) -> list[discord.File]:
    """Sets the strip as the embed's image and returns the file to send with it.

    Empty when none of the Legends have art or rendering fails — the embed
    then goes out exactly as it would have without portraits.
    """
    if not legend_name_keys:
        return []
    try:
        png = await asyncio.to_thread(render_legend_strip, list(legend_name_keys))
    except Exception:
        logger.exception("Failed to render Legend strip for %s", list(legend_name_keys))
        return []
    if png is None:
        return []
    embed.set_image(url=f"attachment://{_FILENAME}")
    return [discord.File(io.BytesIO(png), filename=_FILENAME)]
