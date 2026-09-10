"""Server-themed generated imagery — docs/DECISIONS.md ADR-059.

Pure-function checks only (no Discord needed), matching this repo's
Discord-agnostic-service testing convention.
"""

from __future__ import annotations

import io

from PIL import Image

from services.image_service import (
    _LOGO_PATH,
    _SUBTITLE_FONT_PATH,
    _TITLE_FONT_PATH,
    CARD_HEIGHT,
    CARD_WIDTH,
    _faded_logo,
    _load_fonts,
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
    assert len(png_bytes) > 0


def test_render_milestone_card_handles_empty_strings() -> None:
    png_bytes = render_milestone_card(title="", subtitle="")
    image = Image.open(io.BytesIO(png_bytes))
    assert image.size == (CARD_WIDTH, CARD_HEIGHT)


def test_logo_asset_ships_inside_src() -> None:
    """The crest must live under src/ (not web/), which the bot's
    Dockerfile deliberately excludes via .dockerignore — docs/DECISIONS.md
    ADR-060. A missing asset here would mean it's missing in production too.
    """
    assert _LOGO_PATH.exists()
    assert "src" in _LOGO_PATH.parts
    assert "web" not in _LOGO_PATH.parts


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


def test_load_fonts_returns_truetype_fonts_from_the_bundled_files() -> None:
    from PIL import ImageFont

    title_font, subtitle_font = _load_fonts(title_size=56, subtitle_size=28)
    assert isinstance(title_font, ImageFont.FreeTypeFont)
    assert isinstance(subtitle_font, ImageFont.FreeTypeFont)


def test_faded_logo_returns_a_faded_rgba_image() -> None:
    logo = _faded_logo(target_height=100, max_opacity=90)
    assert logo is not None
    assert logo.mode == "RGBA"
    assert logo.height == 100
    alpha = logo.getchannel("A")
    assert max(alpha.getdata()) <= 90
