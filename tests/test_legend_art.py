"""Legend portrait lookup + strip rendering (docs/DECISIONS.md ADR-098)."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from services.legend_art import (
    available_portraits,
    legend_display_name,
    legend_portrait_path,
    normalize_legend_key,
    render_legend_strip,
)

_WEB_PORTRAITS = Path(__file__).resolve().parents[1] / "web" / "assets" / "img" / "legend-portraits"


def test_normalize_handles_spaces_underscores_case_and_diacritics() -> None:
    assert normalize_legend_key("Lord Vraxx") == "lord_vraxx"
    assert normalize_legend_key("lord_vraxx") == "lord_vraxx"
    assert normalize_legend_key("  WU SHANG ") == "wu_shang"
    assert normalize_legend_key("Bödvar") == "bodvar"


def test_display_name_title_cases_either_key_shape() -> None:
    assert legend_display_name("sir roland") == "Sir Roland"
    assert legend_display_name("sir_roland") == "Sir Roland"


def test_portrait_lookup_normalizes_and_misses_cleanly() -> None:
    assert legend_portrait_path("Queen Nai") is not None
    assert legend_portrait_path("not_a_legend") is None


def test_the_packaged_roster_is_complete_enough() -> None:
    portraits = available_portraits()
    assert len(portraits) >= 60
    assert {"bodvar", "hattori", "orion", "mordex", "nix", "lord_vraxx"} <= portraits


def test_bot_and_website_ship_the_same_roster() -> None:
    web = {path.stem for path in _WEB_PORTRAITS.glob("*.webp")}
    assert web == set(available_portraits())


def test_strip_skips_legends_without_art() -> None:
    png = render_legend_strip(["mordex", "not_a_legend", "nix"])
    assert png is not None
    with_two = Image.open(io.BytesIO(png))
    one = Image.open(io.BytesIO(render_legend_strip(["mordex"]) or b""))
    assert with_two.width > one.width
    assert with_two.height == one.height


def test_strip_is_none_when_nothing_has_art() -> None:
    assert render_legend_strip(["not_a_legend"]) is None
    assert render_legend_strip([]) is None
