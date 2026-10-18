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


def _draw_gradient_text(
    image: Image.Image,
    text: str,
    *,
    box: tuple[int, int, int, int],
    font_path: Path,
    stops: list[tuple[float, tuple[int, int, int]]],
    initial_size: int,
    min_size: int,
    margin: int = _NAME_MARGIN,
    stroke: int = 0,
) -> None:
    """Set one horizontal line of text into `box` on `image`, in place
    (docs/DECISIONS.md ADR-122, ADR-124).

    The text gets a left-to-right gradient spanning the text itself (so a
    short string still shows every stop), over a soft dark shadow and a faint
    glow in the gradient's middle colour. It shrinks to fit, is centred on
    cap height (so descenders don't lift it), and anything still too wide at
    `min_size` is condensed horizontally rather than shrunk further.
    `stroke` thickens the glyphs (a bolder cut of a single-weight font).
    """
    x0, y0, x1, y1 = box
    center_x = (x0 + x1) // 2
    center_y = (y0 + y1) // 2

    max_width = (x1 - x0) - margin * 2
    font = _fit_font(
        text,
        font_path,
        variation=None,
        max_width=max_width - stroke * 2,
        initial_size=initial_size,
        min_size=min_size,
        step=2,
    )
    cap_height = -font.getbbox("H", anchor="ls")[1]
    baseline = center_y + round(cap_height / 2)

    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).text(
        (center_x, baseline),
        text,
        font=font,
        fill=255,
        anchor="ms",
        stroke_width=stroke,
        stroke_fill=255,
    )
    ink = mask.getbbox()
    if ink is not None and ink[2] - ink[0] > max_width:
        glyphs = mask.crop(ink).resize((max_width, ink[3] - ink[1]), Image.Resampling.LANCZOS)
        mask = Image.new("L", image.size, 0)
        mask.paste(glyphs, (center_x - max_width // 2, ink[1]))
        ink = mask.getbbox()
    if ink is None:
        return

    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(4)).point(lambda a: int(a * 0.8)))
    image.alpha_composite(shadow, dest=(0, 2))
    image.alpha_composite(_glow(mask, _stop_colour(0.5, stops), blur_radius=10, boost=0.5))

    fill = _horizontal_gradient_multi(ink[2] - ink[0], ink[3] - ink[1], stops).convert("RGBA")
    fill.putalpha(mask.crop(ink))
    image.alpha_composite(fill, dest=(ink[0], ink[1]))


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
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
    "Goodbye" titles; this sets one dynamic string, the member's name
    (Inter ExtraBold), horizontally into the template's empty name plate.
    """
    image = Image.open(template_path).convert("RGBA")
    _draw_gradient_text(
        image,
        member_name,
        box=box,
        font_path=_NAME_FONT_PATH,
        stops=stops,
        initial_size=46,
        min_size=18,
    )
    return _png(image)


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


# --- Achievement card (docs/DECISIONS.md ADR-124) ----------------------------

# The owner's BRAWLISTAN achievement artwork (docs/brand/achievement-card-
# master.png). Everything on it is static except three things: the badge in
# the circle, the achievement name in the middle plate, and the username in
# the bottom plate (right of the printed avatar glyph). Measured against the
# artwork; the circle's lower edge sits behind the name plate, so the badge
# is centred on the circle's visible part.
_ACHIEVEMENT_CARD_PATH = _ASSETS_DIR / "img" / "achievement_card_template.png"
_ACHIEVEMENT_ICONS_DIR = _ASSETS_DIR / "achievement_icons"
_ACHIEVEMENT_NAME_FONT_PATH = _ASSETS_DIR / "fonts" / "Bangers-Regular.ttf"
ACHIEVEMENT_CARD_WIDTH = 1672
ACHIEVEMENT_CARD_HEIGHT = 941
_BADGE_CENTER = (836, 484)
_BADGE_RING_RADIUS = 112
_BADGE_RING_WIDTH = 10
_BADGE_ICON_SIZE = 150
_ACHIEVEMENT_NAME_BOX = (640, 626, 1032, 686)
_ACHIEVEMENT_USER_BOX = (662, 748, 1118, 814)

_EMERALD_RGB = (0x00, 0xE6, 0x76)
_ACHIEVEMENT_NAME_STOPS: list[tuple[float, tuple[int, int, int]]] = [
    (0.0, (0xFF, 0xFF, 0xFF)),
    (0.5, (0x42, 0xFF, 0xD2)),
    (1.0, (0xD9, 0x46, 0xEF)),
]
_BADGE_RING_STOPS: list[tuple[float, tuple[int, int, int]]] = [
    (0.0, (0xD9, 0x46, 0xEF)),
    (0.5, (0x42, 0xFF, 0xD2)),
    (1.0, (0xD6, 0xA8, 0x4F)),
]


def achievement_icon_path(achievement_key: str) -> Path:
    """The bundled badge for an achievement (scripts/achievement_icons.py),
    or the default medal for one without its own."""
    path = _ACHIEVEMENT_ICONS_DIR / f"{achievement_key}.png"
    return path if path.is_file() else _ACHIEVEMENT_ICONS_DIR / "_default.png"


def _diagonal_gradient(size: int, stops: list[tuple[float, tuple[int, int, int]]]) -> Image.Image:
    """A square 135-degree gradient: the first stop top-left, the last bottom-right."""
    small = 64
    grid = Image.new("RGB", (small, small))
    grid.putdata(
        [
            _stop_colour((x + y) / (2 * (small - 1)), stops)
            for y in range(small)
            for x in range(small)
        ]
    )
    return grid.resize((size, size), Image.Resampling.BICUBIC)


def _ring_mask(size: int, *, radius: int, width: int) -> Image.Image:
    """An anti-aliased ring, drawn 4x and scaled down."""
    scale = 4
    big = Image.new("L", (size * scale, size * scale), 0)
    draw = ImageDraw.Draw(big)
    c = size * scale // 2
    outer, inner = radius * scale, (radius - width) * scale
    draw.ellipse((c - outer, c - outer, c + outer, c + outer), fill=255)
    draw.ellipse((c - inner, c - inner, c + inner, c + inner), fill=0)
    return big.resize((size, size), Image.Resampling.LANCZOS)


def _draw_badge(image: Image.Image, icon: Image.Image | None) -> None:
    cx, cy = _BADGE_CENTER
    size = (_BADGE_RING_RADIUS + 40) * 2
    origin = (cx - size // 2, cy - size // 2)

    # Emerald energy behind the badge, then the gradient ring with its own glow.
    halo = Image.new("L", (size, size), 0)
    r = _BADGE_RING_RADIUS - 10
    ImageDraw.Draw(halo).ellipse((size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r), 90)
    halo_layer = Image.new("RGBA", (size, size), (*_EMERALD_RGB, 0))
    halo_layer.putalpha(halo.filter(ImageFilter.GaussianBlur(28)))
    image.alpha_composite(halo_layer, dest=origin)

    ring = _ring_mask(size, radius=_BADGE_RING_RADIUS, width=_BADGE_RING_WIDTH)
    gradient = _diagonal_gradient(size, _BADGE_RING_STOPS).convert("RGBA")
    glow = gradient.copy()
    glow.putalpha(ring.filter(ImageFilter.GaussianBlur(8)).point(lambda a: int(a * 1.2)))
    image.alpha_composite(glow, dest=origin)
    gradient.putalpha(ring)
    image.alpha_composite(gradient, dest=origin)

    if icon is None:
        return
    badge = icon.convert("RGBA")
    badge.thumbnail((_BADGE_ICON_SIZE, _BADGE_ICON_SIZE), Image.Resampling.LANCZOS)
    shadow = Image.new("RGBA", badge.size, (0, 0, 0, 0))
    shadow.putalpha(
        badge.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda a: a // 2)
    )
    dest = (cx - badge.width // 2, cy - badge.height // 2)
    image.alpha_composite(shadow, dest=(dest[0], dest[1] + 5))
    image.alpha_composite(badge, dest=dest)


def render_achievement_card(
    *, achievement_icon: Path | Image.Image | None, achievement_name: str, username: str
) -> bytes:
    """The BRAWLISTAN achievement card (docs/DECISIONS.md ADR-124).

    `achievement_icon` is a badge image (or its path; see
    `achievement_icon_path`), drawn inside a 135-degree magenta-cyan-gold
    ring. `achievement_name` is set in Bangers with a white-cyan-magenta
    gradient, and `username` in Inter ExtraBold, white to mint. Everything
    else is the artwork's own.
    """
    image = Image.open(_ACHIEVEMENT_CARD_PATH).convert("RGBA")

    icon: Image.Image | None
    if isinstance(achievement_icon, Path):
        try:
            icon = Image.open(achievement_icon)
        except OSError:
            icon = None
    else:
        icon = achievement_icon
    _draw_badge(image, icon)

    _draw_gradient_text(
        image,
        achievement_name,
        box=_ACHIEVEMENT_NAME_BOX,
        font_path=_ACHIEVEMENT_NAME_FONT_PATH,
        stops=_ACHIEVEMENT_NAME_STOPS,
        initial_size=56,
        min_size=24,
        stroke=1,
    )
    _draw_gradient_text(
        image,
        username,
        box=_ACHIEVEMENT_USER_BOX,
        font_path=_NAME_FONT_PATH,
        stops=_GOODBYE_NAME_STOPS,
        initial_size=44,
        min_size=18,
    )
    return _png(image)


# --- Clan Wars result card (docs/DECISIONS.md ADR-136) ----------------------

CLAN_WAR_CARD_SIZE = (1200, 630)
_CW_BG = (10, 6, 6)
_CW_EMBER = (255, 106, 31)
_CW_FIRE = (255, 46, 58)
_CW_CREAM = (251, 249, 216)
_CW_MUTED = (190, 176, 160)
_CW_GOLD = (242, 193, 78)


def _hex_rgb(value: str | None, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if not value or len(value) != 7 or not value.startswith("#"):
        return default
    try:
        return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
    except ValueError:
        return default


def render_clan_war_card(
    *,
    week_label: str,
    standings: list[tuple[str, str, int, str | None]],
    mvp: tuple[str, int, str | None] | None,
    site: str,
) -> bytes:
    """The shareable weekly Clan Wars result: the winner large, the next
    places, the MVP and the site. `standings` is (name, tag, points, accent
    colour) best first; `mvp` is (player name, points, team tag)."""
    width, height = CLAN_WAR_CARD_SIZE
    image = Image.new("RGBA", CLAN_WAR_CARD_SIZE, (*_CW_BG, 255))

    # A diagonal fire wash and a soft glow behind the winner.
    wash = Image.new("RGBA", CLAN_WAR_CARD_SIZE, (0, 0, 0, 0))
    wd = ImageDraw.Draw(wash)
    for i in range(0, width + height, 6):
        alpha = max(0, 70 - abs(i - 620) // 6)
        wd.line([(i, 0), (i - height, height)], fill=(*_CW_FIRE, alpha), width=6)
    image = Image.alpha_composite(image, wash.filter(ImageFilter.GaussianBlur(18)))
    glow = Image.new("RGBA", CLAN_WAR_CARD_SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-120, 80, 760, 560), fill=(*_CW_EMBER, 60))
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(80)))

    draw = ImageDraw.Draw(image)
    label_font = _fit_font(
        "CLAN WARS",
        _SUBTITLE_FONT_PATH,
        variation=None,
        max_width=600,
        initial_size=34,
        min_size=20,
    )
    draw.text((64, 52), "CLAN WARS", font=label_font, fill=_CW_EMBER)
    draw.text(
        (64 + draw.textlength("CLAN WARS  ", font=label_font), 52),
        f"· {week_label.upper()}",
        font=label_font,
        fill=_CW_MUTED,
    )

    if standings:
        name, tag, points, accent = standings[0]
        accent_rgb = _hex_rgb(accent, _CW_EMBER)
        draw.rectangle((64, 120, 72, 300), fill=accent_rgb)
        draw.text((92, 116), "WEEK WINNER", font=label_font, fill=_CW_GOLD)
        winner_font = _fit_font(
            name, _NAME_FONT_PATH, variation=None, max_width=720, initial_size=96, min_size=40
        )
        draw.text((90, 160), name, font=winner_font, fill=_CW_CREAM)
        sub_font = _fit_font(
            "x", _SUBTITLE_FONT_PATH, variation=None, max_width=600, initial_size=40, min_size=40
        )
        draw.text((92, 262), f"[{tag}]  ·  {points:,} PTS", font=sub_font, fill=_CW_EMBER)

        row_font = _fit_font(
            "x", _NAME_FONT_PATH, variation=None, max_width=600, initial_size=30, min_size=30
        )
        pts_font = _fit_font(
            "x", _SUBTITLE_FONT_PATH, variation=None, max_width=300, initial_size=34, min_size=34
        )
        y = 350
        for place, (r_name, r_tag, r_points, r_accent) in enumerate(standings[1:4], start=2):
            draw.ellipse((66, y + 6, 90, y + 30), fill=_hex_rgb(r_accent, _CW_MUTED))
            text = f"{place}.  {r_name} [{r_tag}]"
            while draw.textlength(text, font=row_font) > 560 and len(r_name) > 4:
                r_name = r_name[:-2]
                text = f"{place}.  {r_name}… [{r_tag}]"
            draw.text((106, y), text, font=row_font, fill=_CW_CREAM)
            draw.text((700, y + 2), f"{r_points:,} pts", font=pts_font, fill=_CW_MUTED)
            y += 52

    if mvp is not None:
        mvp_name, mvp_points, mvp_tag = mvp
        box = (820, 120, 1136, 300)
        draw.rounded_rectangle(box, radius=24, fill=(30, 18, 14, 255), outline=_CW_GOLD, width=3)
        star_font = _fit_font(
            "x", _SUBTITLE_FONT_PATH, variation=None, max_width=200, initial_size=30, min_size=30
        )
        draw.text((848, 140), "MVP OF THE WEEK", font=star_font, fill=_CW_GOLD)
        mvp_font = _fit_font(
            mvp_name, _NAME_FONT_PATH, variation=None, max_width=260, initial_size=48, min_size=22
        )
        draw.text((848, 184), mvp_name, font=mvp_font, fill=_CW_CREAM)
        draw.text(
            (848, 246),
            f"{mvp_points:,} pts" + (f" · [{mvp_tag}]" if mvp_tag else ""),
            font=star_font,
            fill=_CW_EMBER,
        )

    foot_font = _fit_font(
        site, _SUBTITLE_FONT_PATH, variation=None, max_width=700, initial_size=30, min_size=18
    )
    draw.line((64, 560, width - 64, 560), fill=(255, 255, 255, 40), width=1)
    draw.text((64, 574), site, font=foot_font, fill=_CW_CREAM)
    tagline = "A new war every week · join the Discord"
    draw.text(
        (width - 64 - draw.textlength(tagline, font=foot_font), 574),
        tagline,
        font=foot_font,
        fill=_CW_MUTED,
    )
    return _png(image)
