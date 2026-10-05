"""Server-themed generated imagery — Discord-agnostic (docs/ARCHITECTURE.md).

Renders a branded milestone/achievement PNG by compositing dynamic text
onto the clan's own achievement-frame artwork, rather than calling an
external AI image API (none is configured for this project — docs/
DECISIONS.md ADR-059) or building the background procedurally (the
original approach — docs/DECISIONS.md ADR-059/ADR-060 — replaced by this
template-based one in ADR-062, after prototyping the text treatment in
isolation first).

The template (src/assets/img/achievement_template.png) already carries the
clan's full branding — crest, gradient, corner taglines in English and
Urdu — so this module's only job is to set the two dynamic strings (an
announcement's headline and its description) into the template's empty
content area with a metallic-gold "bevel & highlight" text treatment that
matches the crest's own styling: a gold-to-bronze gradient fill, a carved-
medallion highlight band, a thin dark stroke, subtle extrusion for depth,
and a soft glow. Long strings shrink to fit rather than overflowing or
getting clipped (`_fit_font`).

Both bundled fonts (Orbitron for the headline, Rajdhani SemiBold for the
description) live at src/assets/fonts/, and the template lives at
src/assets/img/ — both inside src/, which the Dockerfile's `COPY src/
./src/` already copies whole, so nothing here needs a Dockerfile change.
No Urdu is rendered dynamically: the headline/description are arbitrary
runtime strings (a Discord display name, an achievement's name) with no
Urdu translation available, so bilingual brand presence stays where it
already lives — baked into the template's own corner artwork.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from bot.palette import GOLD

# --- Paths ----------------------------------------------------------------

_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_TEMPLATE_PATH = _ASSETS_DIR / "img" / "achievement_template.png"
_WELCOME_TEMPLATE_PATH = _ASSETS_DIR / "img" / "welcome_template.png"
_GOODBYE_TEMPLATE_PATH = _ASSETS_DIR / "img" / "goodbye_template.png"
_TITLE_FONT_PATH = _ASSETS_DIR / "fonts" / "Orbitron-Variable.ttf"
_SUBTITLE_FONT_PATH = _ASSETS_DIR / "fonts" / "Rajdhani-SemiBold.ttf"

# The template's own dimensions — the whole card *is* the template now,
# not a small canvas composited with a separate watermark.
CARD_WIDTH = 1672
CARD_HEIGHT = 941

# The safe content rectangle inside the template's dark cutout — inset
# from the gold frame and the diamond ornaments top/bottom center
# (confirmed visually against the template asset).
_CUTOUT_BOX = (330, 355, 1345, 745)
_CUTOUT_TEXT_MARGIN = 60  # keeps long strings clear of the gold frame edges

# welcome_template.png / goodbye_template.png: the owner's BRAWLISTAN banners,
# split from one stacked composite (docs/brand/welcome-goodbye-master.png,
# docs/DECISIONS.md ADR-122). Both are 1942x402; each has its own empty
# name plate, measured against the artwork, inset clear of the neon frame and
# the diamond ornaments top and bottom centre.
WELCOME_CARD_WIDTH = 1942
WELCOME_CARD_HEIGHT = 402
_WELCOME_NAME_BOX = (760, 268, 1185, 334)
_GOODBYE_NAME_BOX = (760, 234, 1185, 308)
_NAME_MARGIN = 16  # keeps a long name's glow off the plate's slanted ends

# The username: Inter ExtraBold, always horizontal, with a left-to-right (0°)
# gradient across the name. Welcome takes the energetic version; goodbye the
# calmer one.
_NAME_FONT_PATH = _ASSETS_DIR / "fonts" / "Inter-ExtraBold.ttf"
_WELCOME_NAME_STOPS: list[tuple[float, tuple[int, int, int]]] = [
    (0.0, (0xFF, 0xFF, 0xFF)),
    (0.5, (0x42, 0xFF, 0xD2)),
    (1.0, (0xC0, 0x84, 0xFC)),
]
_GOODBYE_NAME_STOPS: list[tuple[float, tuple[int, int, int]]] = [
    (0.0, (0xFF, 0xFF, 0xFF)),
    (1.0, (0xA7, 0xFF, 0xF0)),
]

# --- Brand colors -----------------------------------------------------------

_GOLD_RGB = ((GOLD >> 16) & 0xFF, (GOLD >> 8) & 0xFF, GOLD & 0xFF)
_HIGHLIGHT_RGB = (255, 236, 180)
_BRONZE_RGB = (150, 110, 40)
_STROKE_RGB = (28, 20, 8)

_GRADIENT_STOPS: list[tuple[float, tuple[int, int, int]]] = [
    (0.0, _HIGHLIGHT_RGB),
    (0.5, _GOLD_RGB),
    (1.0, _BRONZE_RGB),
]


def _lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _stop_colour(t: float, stops: list[tuple[float, tuple[int, int, int]]]) -> tuple[int, int, int]:
    lo, hi = stops[0], stops[-1]
    for i in range(len(stops) - 1):
        if stops[i][0] <= t <= stops[i + 1][0]:
            lo, hi = stops[i], stops[i + 1]
            break
    span = hi[0] - lo[0]
    local_t = 0.0 if span <= 0 else (t - lo[0]) / span
    return _lerp_rgb(lo[1], hi[1], local_t)


def _vertical_gradient_multi(
    width: int, height: int, stops: list[tuple[float, tuple[int, int, int]]]
) -> Image.Image:
    """A vertical gradient through an arbitrary number of (position 0..1,
    rgb) stops — a gold-to-bronze metallic fill rather than a flat color.
    """
    column = Image.new("RGB", (1, max(1, height)))
    column.putdata([_stop_colour(y / max(1, height - 1), stops) for y in range(max(1, height))])
    return column.resize((max(1, width), max(1, height)))


def _horizontal_gradient_multi(
    width: int, height: int, stops: list[tuple[float, tuple[int, int, int]]]
) -> Image.Image:
    """The same, left to right (a 0° gradient)."""
    row = Image.new("RGB", (max(1, width), 1))
    row.putdata([_stop_colour(x / max(1, width - 1), stops) for x in range(max(1, width))])
    return row.resize((max(1, width), max(1, height)))


# --- Font fitting -----------------------------------------------------------


def _fit_font(
    text: str,
    font_path: Path,
    *,
    variation: str | None,
    max_width: int,
    initial_size: int,
    min_size: int,
    step: int = 4,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """The largest size (down to `min_size`) at which `text` fits within
    `max_width`, so a long display name or achievement description
    shrinks to fit instead of overflowing the cutout or getting clipped.
    Falls back to Pillow's generic default font if the bundled file is
    ever missing/unreadable — a card with the wrong font is fine, a
    crash losing the whole announcement is not.
    """

    def load(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont | None:
        try:
            font = ImageFont.truetype(str(font_path), size)
        except OSError:
            return None
        if variation:
            with contextlib.suppress(OSError):
                font.set_variation_by_name(variation)
        return font

    dummy_draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    size = initial_size
    while size > min_size:
        font = load(size)
        if font is None:
            return ImageFont.load_default(size=initial_size)
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= step

    return load(min_size) or ImageFont.load_default(size=min_size)


# --- Text masks ---------------------------------------------------------


def _make_masks(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    *,
    padding: int,
    stroke_width: int,
) -> tuple[Image.Image, Image.Image]:
    """Returns (inner_mask, outer_mask) — outer includes `stroke_width`,
    both drawn onto the same canvas at the same offset so they're pixel-
    aligned for compositing. "L" mode, 0=transparent, 255=opaque glyph.
    """
    dummy = Image.new("L", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = int(bbox[2] - bbox[0]) + padding * 2
    height = int(bbox[3] - bbox[1]) + padding * 2
    x = padding - bbox[0]
    y = padding - bbox[1]

    inner = Image.new("L", (width, height), 0)
    ImageDraw.Draw(inner).text((x, y), text, font=font, fill=255)

    outer = Image.new("L", (width, height), 0)
    if stroke_width:
        ImageDraw.Draw(outer).text(
            (x, y), text, font=font, fill=255, stroke_width=stroke_width, stroke_fill=255
        )
    else:
        outer.paste(inner)
    return inner, outer


# --- Effect layers ------------------------------------------------------


def _gradient_fill_mask(
    mask: Image.Image, stops: list[tuple[float, tuple[int, int, int]]]
) -> Image.Image:
    grad = _vertical_gradient_multi(mask.width, mask.height, stops).convert("RGBA")
    grad.putalpha(mask)
    return grad


def _glow(
    mask: Image.Image, colour: tuple[int, int, int], *, blur_radius: float, boost: float
) -> Image.Image:
    boosted = mask.point(lambda a: min(255, int(a * boost)))
    blurred = boosted.filter(ImageFilter.GaussianBlur(blur_radius))
    glow = Image.new("RGBA", mask.size, (*colour, 0))
    glow.putalpha(blurred)
    return glow


def _extrude(
    mask: Image.Image,
    *,
    steps: int,
    offset: tuple[int, int],
    near_colour: tuple[int, int, int],
    far_colour: tuple[int, int, int],
) -> Image.Image:
    """Stacks `steps` diagonally-offset copies of `mask`, darkening toward
    `far_colour` with distance, for a subtle carved-metal depth effect.
    """
    canvas = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    for i in range(steps, 0, -1):
        t = i / steps
        colour = _lerp_rgb(near_colour, far_colour, t)
        solid = Image.new("RGBA", mask.size, (*colour, 0))
        solid.putalpha(mask)
        shifted = Image.new("RGBA", mask.size, (0, 0, 0, 0))
        shifted.paste(solid, (i * offset[0], i * offset[1]), solid)
        canvas.alpha_composite(shifted)
    return canvas


def _bevel_highlight(
    mask: Image.Image, colour: tuple[int, int, int], *, band_fraction: float = 0.45
) -> Image.Image:
    """A soft top-lit highlight confined to the glyph shape — a carved-
    medallion look without true 3D lighting.
    """
    width, height = mask.size
    band_height = max(1, int(height * band_fraction))
    column = [int(255 * (1 - y / band_height)) if y < band_height else 0 for y in range(height)]
    band = Image.new("L", (1, height))
    band.putdata(column)
    band = band.resize((width, height))
    combined_alpha = ImageChops.multiply(mask, band)
    highlight = Image.new("RGBA", (width, height), (*colour, 0))
    highlight.putalpha(combined_alpha)
    return highlight


def _render_styled_text(
    text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, *, padding: int = 40
) -> Image.Image:
    """The "bevel & highlight" treatment: subtle extrusion -> dark stroke
    ring -> metallic gradient fill -> top-band highlight -> moderate
    glow, layered into one RGBA image ready to composite onto the
    template. One fixed style, reused for both the headline and the
    description (different font/size only).
    """
    inner_mask, outer_mask = _make_masks(text, font, padding=padding, stroke_width=2)
    size = inner_mask.size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))

    layer.alpha_composite(_glow(outer_mask, _GOLD_RGB, blur_radius=8, boost=1.2))
    layer.alpha_composite(
        _extrude(
            outer_mask,
            steps=4,
            offset=(1, 1),
            near_colour=(120, 90, 38),
            far_colour=(30, 20, 8),
        )
    )

    stroke_solid = Image.new("RGBA", size, (*_STROKE_RGB, 255))
    stroke_solid.putalpha(outer_mask)
    layer.alpha_composite(stroke_solid)

    layer.alpha_composite(_gradient_fill_mask(inner_mask, _GRADIENT_STOPS))

    highlight = _bevel_highlight(inner_mask, (255, 250, 230))
    highlight.putalpha(highlight.getchannel("A").point(lambda a: int(a * 0.55)))
    layer.alpha_composite(highlight)

    return layer


def _trim(layer: Image.Image, *, alpha_threshold: int = 14) -> Image.Image:
    """Crops away the mask padding down to the actually-painted content
    (ignoring near-invisible glow tail below `alpha_threshold`), so
    layout math works off real rendered size, not the padded canvas.
    """
    solid = layer.getchannel("A").point(lambda a: 255 if a >= alpha_threshold else 0)
    bbox = solid.getbbox()
    return layer.crop(bbox) if bbox else layer


# --- Composition ----------------------------------------------------------


def render_milestone_card(*, title: str, subtitle: str) -> bytes:
    """A branded card for a milestone/achievement announcement: `title`
    (e.g. a member's display name) set large, `subtitle` (e.g. the
    achievement's name or a new peak rating) set below it, both in the
    metallic gold "bevel & highlight" style, composited into the clan's
    achievement-frame template.
    """
    template = Image.open(_TEMPLATE_PATH).convert("RGBA")
    image = template.copy()

    x0, y0, x1, y1 = _CUTOUT_BOX
    center_x = (x0 + x1) // 2
    cutout_height = y1 - y0
    max_text_width = (x1 - x0) - _CUTOUT_TEXT_MARGIN * 2

    title_font = _fit_font(
        title,
        _TITLE_FONT_PATH,
        variation="Bold",
        max_width=max_text_width,
        initial_size=88,
        min_size=36,
    )
    subtitle_font = _fit_font(
        subtitle,
        _SUBTITLE_FONT_PATH,
        variation=None,
        max_width=max_text_width,
        initial_size=40,
        min_size=20,
    )

    title_layer = _trim(_render_styled_text(title, title_font))
    subtitle_layer = _trim(_render_styled_text(subtitle, subtitle_font))

    def row_top(layer: Image.Image, center_fraction: float) -> int:
        center_y = y0 + round(cutout_height * center_fraction)
        return center_y - layer.height // 2

    def paste_centered(layer: Image.Image, top_y: int) -> None:
        image.alpha_composite(layer, dest=(center_x - layer.width // 2, top_y))

    paste_centered(title_layer, row_top(title_layer, 0.42))
    paste_centered(subtitle_layer, row_top(subtitle_layer, 0.66))

    buffer = io.BytesIO()
    # optimize=True costs several seconds for a few percent smaller output
    # on an image this size (measured) — not worth it for a render this
    # infrequent (one per announcement) to risk blocking the event loop.
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _render_arrival_card(
    template_path: Path,
    *,
    member_name: str,
    box: tuple[int, int, int, int],
    stops: list[tuple[float, tuple[int, int, int]]],
) -> bytes:
    """Shared renderer for the welcome/goodbye cards (docs/DECISIONS.md
    ADR-122). The banners carry their own tilted "Welcome to BRAWLISTAN" /
    "Goodbye" titles; this sets one dynamic string, the member's name,
    horizontally into the template's empty name plate.

    The name is Inter ExtraBold with a left-to-right gradient spanning the
    name itself (so a short name still shows every stop), over a soft dark
    shadow and a faint glow in the gradient's middle colour. Capitals are
    centred on the plate's middle, so names with descenders don't sit high.
    """
    image = Image.open(template_path).convert("RGBA")

    x0, y0, x1, y1 = box
    center_x = (x0 + x1) // 2
    center_y = (y0 + y1) // 2

    max_width = (x1 - x0) - _NAME_MARGIN * 2
    font = _fit_font(
        member_name,
        _NAME_FONT_PATH,
        variation=None,
        max_width=max_width,
        initial_size=46,
        min_size=18,
        step=2,
    )
    cap_height = -font.getbbox("H", anchor="ls")[1]
    baseline = center_y + round(cap_height / 2)

    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).text((center_x, baseline), member_name, font=font, fill=255, anchor="ms")
    ink = mask.getbbox()
    if ink is not None and ink[2] - ink[0] > max_width:
        # Still too wide at the smallest readable size (a 32-character name of
        # wide letters): condense it horizontally rather than shrink it further.
        glyphs = mask.crop(ink).resize((max_width, ink[3] - ink[1]), Image.Resampling.LANCZOS)
        mask = Image.new("L", image.size, 0)
        mask.paste(glyphs, (center_x - max_width // 2, ink[1]))
        ink = mask.getbbox()
    if ink is not None:
        shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(4)).point(lambda a: int(a * 0.8)))
        image.alpha_composite(shadow, dest=(0, 2))
        image.alpha_composite(_glow(mask, _stop_colour(0.5, stops), blur_radius=10, boost=0.5))

        fill = _horizontal_gradient_multi(ink[2] - ink[0], ink[3] - ink[1], stops).convert("RGBA")
        fill.putalpha(mask.crop(ink))
        image.alpha_composite(fill, dest=(ink[0], ink[1]))

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def render_welcome_card(*, member_name: str) -> bytes:
    """A branded welcome card for a new member (docs/DECISIONS.md ADR-122)."""
    return _render_arrival_card(
        _WELCOME_TEMPLATE_PATH,
        member_name=member_name,
        box=_WELCOME_NAME_BOX,
        stops=_WELCOME_NAME_STOPS,
    )


def render_goodbye_card(*, member_name: str) -> bytes:
    """A branded goodbye card for a departing member (docs/DECISIONS.md ADR-122)."""
    return _render_arrival_card(
        _GOODBYE_TEMPLATE_PATH,
        member_name=member_name,
        box=_GOODBYE_NAME_BOX,
        stops=_GOODBYE_NAME_STOPS,
    )
