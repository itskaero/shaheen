"""Server-themed generated imagery — Discord-agnostic (docs/ARCHITECTURE.md).

Renders PNG bytes procedurally with Pillow from bot.palette's brand colors,
rather than calling an external AI image API (none is configured for this
project — docs/DECISIONS.md ADR-059). Deliberately modest for a first
pass: one generator, a branded milestone/achievement card, attached as a
discord.File by bot/cogs/clan.py's existing announcement path.

Uses ImageFont.load_default(size=...) (Pillow >= 10.1) rather than a
bundled or system font file — the Dockerfile's python:3.12-slim base has
no fonts installed, and shipping a TTF asset is unnecessary scope for a
first pass when Pillow already bundles a scalable default font.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from bot.palette import CREAM, EMERALD, FOREST_GREEN, GOLD

CARD_WIDTH = 800
CARD_HEIGHT = 300


def _hex_to_rgb(colour: int) -> tuple[int, int, int]:
    return (colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF


def _diagonal_gradient(
    width: int, height: int, start: tuple[int, int, int], end: tuple[int, int, int]
) -> Image.Image:
    base = Image.new("RGB", (width, height), start)
    top = Image.new("RGB", (width, height), end)
    # Diagonal alpha mask: 0 at top-left, 255 at bottom-right.
    mask = Image.new("L", (width, height))
    mask_data = [
        int(255 * ((x / width) + (y / height)) / 2) for y in range(height) for x in range(width)
    ]
    mask.putdata(mask_data)
    return Image.composite(top, base, mask)


def _centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    canvas_width: int,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((canvas_width - text_width) / 2, y), text, font=font, fill=fill)


def render_milestone_card(*, title: str, subtitle: str) -> bytes:
    """A branded green-to-gold banner card for a milestone/achievement
    announcement — title (e.g. a display name) large, subtitle (e.g. the
    achievement/milestone text) smaller, both centered.
    """
    image = _diagonal_gradient(
        CARD_WIDTH, CARD_HEIGHT, _hex_to_rgb(FOREST_GREEN), _hex_to_rgb(EMERALD)
    )
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.load_default(size=56)
    subtitle_font = ImageFont.load_default(size=28)

    _centered_text(
        draw, title, y=100, font=title_font, fill=_hex_to_rgb(GOLD), canvas_width=CARD_WIDTH
    )
    _centered_text(
        draw, subtitle, y=175, font=subtitle_font, fill=_hex_to_rgb(CREAM), canvas_width=CARD_WIDTH
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
