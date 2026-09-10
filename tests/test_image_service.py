"""Server-themed generated imagery — docs/DECISIONS.md ADR-059.

Pure-function checks only (no Discord needed), matching this repo's
Discord-agnostic-service testing convention.
"""

from __future__ import annotations

import io

from PIL import Image

from services.image_service import CARD_HEIGHT, CARD_WIDTH, render_milestone_card


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
