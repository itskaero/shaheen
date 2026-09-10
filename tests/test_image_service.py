"""Server-themed generated imagery — docs/DECISIONS.md ADR-059/ADR-062.

Pure-function checks only (no Discord needed), matching this repo's
Discord-agnostic-service testing convention.
"""

from __future__ import annotations

import io

from PIL import Image, ImageFont

from services.image_service import (
    _SUBTITLE_FONT_PATH,
    _TEMPLATE_PATH,
    _TITLE_FONT_PATH,
    CARD_HEIGHT,
    CARD_WIDTH,
    _fit_font,
    _make_masks,
    render_milestone_card,
)


def test_render_milestone_card_returns_a_valid_png() -> None:
    png_bytes = render_milestone_card(title="ShaheenPlayer", subtitle="New peak rating: 1800!")

    image = Image.open(io.BytesIO(png_bytes))
    assert image.format == "PNG"
    assert image.size == (CARD_WIDTH, CARD_HEIGHT)


def test_render_milestone_card_handles_long_text_without_raising() -> None:
    png_bytes = render_milestone_card(
        title="A Very Long Display Name Indeed",
        subtitle="Reached Diamond Shaheen tier with a new peak rating of 2200!",
    )
    image = Image.open(io.BytesIO(png_bytes))
    assert image.size == (CARD_WIDTH, CARD_HEIGHT)


def test_render_milestone_card_handles_empty_strings() -> None:
    png_bytes = render_milestone_card(title="", subtitle="")
    image = Image.open(io.BytesIO(png_bytes))
    assert image.size == (CARD_WIDTH, CARD_HEIGHT)


def test_template_asset_ships_inside_src() -> None:
    """The achievement-frame template must live under src/ (not web/),
    which the bot's Dockerfile deliberately excludes via .dockerignore —
    docs/DECISIONS.md ADR-060. A missing asset here would mean it's
    missing in production too.
    """
    assert _TEMPLATE_PATH.exists()
    assert "src" in _TEMPLATE_PATH.parts
    assert "web" not in _TEMPLATE_PATH.parts


def test_brand_fonts_ship_inside_src() -> None:
    """The bundled Orbitron/Rajdhani font files must live under src/ (not
    web/), which the bot's Dockerfile deliberately excludes via
    .dockerignore — docs/DECISIONS.md ADR-060/ADR-061. Missing here means
    missing in production too, silently falling back to the generic font.
    """
    for font_path in (_TITLE_FONT_PATH, _SUBTITLE_FONT_PATH):
        assert font_path.exists()
        assert "src" in font_path.parts
        assert "web" not in font_path.parts


def test_fit_font_shrinks_long_text_to_stay_within_max_width() -> None:
    short_font = _fit_font(
        "Rex", _TITLE_FONT_PATH, variation="Bold", max_width=900, initial_size=88, min_size=36
    )
    long_font = _fit_font(
        "A Very Long Display Name Indeed The Third",
        _TITLE_FONT_PATH,
        variation="Bold",
        max_width=900,
        initial_size=88,
        min_size=36,
    )
    assert isinstance(short_font, ImageFont.FreeTypeFont)
    assert isinstance(long_font, ImageFont.FreeTypeFont)
    assert long_font.size < short_font.size


def test_fit_font_never_goes_below_min_size() -> None:
    font = _fit_font(
        "An Extremely Long String That Cannot Possibly Fit In The Available Width At All",
        _TITLE_FONT_PATH,
        variation="Bold",
        max_width=200,
        initial_size=88,
        min_size=36,
    )
    assert font.size == 36


def test_make_masks_outer_stroke_mask_covers_more_pixels_than_inner() -> None:
    """`_make_masks`' inner/outer masks are drawn at the same canvas
    offset (needed so gradient-fill and stroke-ring layers stay pixel-
    aligned) — same size, but the stroked outer mask should paint a
    strictly larger (fatter) glyph silhouette than the unstroked inner one.
    """
    font = ImageFont.truetype(str(_TITLE_FONT_PATH), 60)
    inner, outer = _make_masks("Shaheen", font, padding=40, stroke_width=3)
    assert outer.size == inner.size

    inner_opaque = sum(1 for a in inner.getdata() if a > 0)
    outer_opaque = sum(1 for a in outer.getdata() if a > 0)
    assert outer_opaque > inner_opaque
