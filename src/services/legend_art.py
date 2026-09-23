"""Legend portrait art for Discord and the website (docs/DECISIONS.md ADR-098).

The portraits (src/assets/legends/<key>.png, and the same crops as .webp
under web/assets/img/legend-portraits/) were cut from the owner-supplied
roster sheet. Discord-agnostic like services/image_service.py: callers get a
path or PNG bytes and decide how to attach them.

Keys are normalised before lookup because the stored `legend_name_key` is
whatever the Brawlhalla API sent — lowercase, but multi-word Legends may
come through with a space ("lord vraxx") or an underscore, and Bödvar may
carry its umlaut. A Legend with no portrait (a new release, or one the
sheet didn't include) simply has no art; nothing here raises for it.
"""

from __future__ import annotations

import io
import unicodedata
from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_PORTRAIT_DIR = _ASSETS_DIR / "legends"
_NAME_FONT_PATH = _ASSETS_DIR / "fonts" / "Rajdhani-SemiBold.ttf"

# Strip layout: portraits are stored at 104x132.
_TILE_W, _TILE_H = 104, 132
_GAP = 10
_PAD = 12
_LABEL_H = 26
_BG = (6, 12, 9)
_FRAME = (212, 175, 55)  # bot.palette.GOLD
_LABEL = (234, 225, 207)


def normalize_legend_key(legend_name_key: str) -> str:
    """Lowercase, ASCII, underscores: `Lord Vraxx` -> `lord_vraxx`, `Bödvar` -> `bodvar`."""
    ascii_key = (
        unicodedata.normalize("NFKD", legend_name_key).encode("ascii", "ignore").decode("ascii")
    )
    return "_".join(ascii_key.strip().lower().replace("-", " ").replace("_", " ").split())


def legend_display_name(legend_name_key: str) -> str:
    return normalize_legend_key(legend_name_key).replace("_", " ").title()


def available_portraits() -> frozenset[str]:
    return frozenset(path.stem for path in _PORTRAIT_DIR.glob("*.png"))


def legend_portrait_path(legend_name_key: str) -> Path | None:
    path = _PORTRAIT_DIR / f"{normalize_legend_key(legend_name_key)}.png"
    return path if path.is_file() else None


def _label_font(draw: ImageDraw.ImageDraw, text: str) -> ImageFont.FreeTypeFont:
    """17px, shrunk until a long name ("KING ZUVA") fits under its tile."""
    for size in range(17, 9, -1):
        font = ImageFont.truetype(str(_NAME_FONT_PATH), size)
        if draw.textlength(text, font=font) <= _TILE_W + _GAP - 2:
            return font
    return font


def render_legend_strip(legend_name_keys: Sequence[str]) -> bytes | None:
    """A row of framed portraits with names underneath, as PNG bytes.

    Legends without art are skipped rather than drawn as a blank tile; None
    when none of them have art, so the caller can leave the embed image off.
    """
    tiles = [
        (key, path) for key in legend_name_keys if (path := legend_portrait_path(key)) is not None
    ]
    if not tiles:
        return None

    width = _PAD * 2 + len(tiles) * _TILE_W + (len(tiles) - 1) * _GAP
    height = _PAD * 2 + _TILE_H + _LABEL_H
    canvas = Image.new("RGB", (width, height), _BG)
    draw = ImageDraw.Draw(canvas)

    for i, (key, path) in enumerate(tiles):
        x = _PAD + i * (_TILE_W + _GAP)
        with Image.open(path) as portrait:
            canvas.paste(portrait.convert("RGB").resize((_TILE_W, _TILE_H)), (x, _PAD))
        draw.rectangle((x - 1, _PAD - 1, x + _TILE_W, _PAD + _TILE_H), outline=_FRAME, width=2)
        name = legend_display_name(key).upper()
        font = _label_font(draw, name)
        text_w = draw.textlength(name, font=font)
        draw.text((x + (_TILE_W - text_w) / 2, _PAD + _TILE_H + 5), name, font=font, fill=_LABEL)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
