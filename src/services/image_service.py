"""Server-themed generated imagery — Discord-agnostic (docs/ARCHITECTURE.md).

Renders PNG bytes procedurally with Pillow from bot.palette's brand colors
and the clan's own crest artwork, rather than calling an external AI image
API (none is configured for this project — docs/DECISIONS.md ADR-059).
Deliberately modest for a first pass: one generator, a branded milestone/
achievement card, attached as a discord.File by bot/cogs/clan.py's
existing announcement path.

Uses ImageFont.load_default(size=...) (Pillow >= 10.1) rather than a
bundled or system font file — the Dockerfile's python:3.12-slim base has
no fonts installed, and shipping a separate TTF asset is unnecessary scope
for a first pass when Pillow already bundles a scalable default font.

The crest logo lives at src/assets/img/logo-icon.png (a copy of the
website's web/assets/img/logo-icon.png) rather than being read from web/,
which the bot's Dockerfile deliberately excludes via .dockerignore — only
src/ ships in the bot's image (docs/DECISIONS.md ADR-060).
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bot.palette import CREAM, FOREST_GREEN, GOLD

CARD_WIDTH = 800
CARD_HEIGHT = 300

_LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "img" / "logo-icon.png"
_LOGO_MAX_OPACITY = 90  # out of 255 (~35%) — a faint watermark, not a sticker
_LOGO_TARGET_HEIGHT = 220


def _hex_to_rgb(colour: int) -> tuple[int, int, int]:
    return (colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF


def _scale_rgb(colour: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, round(channel * factor))) for channel in colour)  # type: ignore[return-value]


def _vertical_gradient(
    width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]
) -> Image.Image:
    base = Image.new("RGB", (width, height), top)
    dest = Image.new("RGB", (width, height), bottom)
    mask = Image.new("L", (1, height), color=0)
    mask.putdata([int(255 * y / height) for y in range(height)])
    mask = mask.resize((width, height))
    return Image.composite(dest, base, mask)


def _faded_logo(*, target_height: int, max_opacity: int) -> Image.Image | None:
    """The crest, resized and faded into a soft radial watermark. Returns
    None (rather than raising) if the asset is somehow missing — a card
    without the watermark is a fine fallback, not worth losing the whole
    render over.
    """
    if not _LOGO_PATH.exists():
        return None

    logo = Image.open(_LOGO_PATH).convert("RGBA")
    scale = target_height / logo.height
    logo = logo.resize((round(logo.width * scale), target_height))

    width, height = logo.size
    cx, cy = width / 2, height / 2
    max_dist = (cx**2 + cy**2) ** 0.5
    radial = Image.new("L", (width, height))
    radial.putdata(
        [
            round(max_opacity * max(0.0, 1 - (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / max_dist))
            for y in range(height)
            for x in range(width)
        ]
    )

    alpha = logo.getchannel("A").point(lambda a: min(a, max_opacity))
    logo.putalpha(Image.composite(alpha, Image.new("L", (width, height), 0), radial))
    return logo


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
    """A branded card for a milestone/achievement announcement: a green
    mid-shade-to-dark-shade gradient with the clan crest faded in as a
    watermark behind centered title/subtitle text.
    """
    mid = _hex_to_rgb(FOREST_GREEN)
    dark = _scale_rgb(mid, 0.28)
    image = _vertical_gradient(CARD_WIDTH, CARD_HEIGHT, mid, dark).convert("RGBA")

    logo = _faded_logo(target_height=_LOGO_TARGET_HEIGHT, max_opacity=_LOGO_MAX_OPACITY)
    if logo is not None:
        position = ((CARD_WIDTH - logo.width) // 2, (CARD_HEIGHT - logo.height) // 2)
        image.alpha_composite(logo, dest=position)

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
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()
