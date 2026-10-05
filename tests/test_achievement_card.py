"""The BRAWLISTAN achievement card and its announcement (docs/DECISIONS.md ADR-124)."""

from __future__ import annotations

import io

from PIL import Image, ImageChops

from bot.content.clan_embeds import build_achievement_congrats
from services.achievements import CATALOG, TOURNAMENT_CHAMPION
from services.image_service import (
    _ACHIEVEMENT_CARD_PATH,
    _ACHIEVEMENT_NAME_BOX,
    _ACHIEVEMENT_NAME_FONT_PATH,
    _ACHIEVEMENT_USER_BOX,
    _BADGE_CENTER,
    ACHIEVEMENT_CARD_HEIGHT,
    ACHIEVEMENT_CARD_WIDTH,
    achievement_icon_path,
    render_achievement_card,
)

SLACK = 8  # a soft glow may spill a few pixels past a plate


def _render(icon: object, name: str, user: str) -> Image.Image:
    png = render_achievement_card(
        achievement_icon=icon,  # type: ignore[arg-type]
        achievement_name=name,
        username=user,
    )
    return Image.open(io.BytesIO(png)).convert("RGB")


def _changed(a: Image.Image, b: Image.Image) -> tuple[int, int, int, int] | None:
    diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > 24 else 0)
    return diff.getbbox()


def _inside(area: tuple[int, int, int, int] | None, box: tuple[int, int, int, int]) -> bool:
    assert area is not None
    x0, y0, x1, y1 = box
    return (
        area[0] >= x0 - SLACK
        and area[1] >= y0 - SLACK
        and area[2] <= x1 + SLACK
        and area[3] <= y1 + SLACK
    )


def test_renders_a_png_at_the_artworks_size() -> None:
    png = render_achievement_card(
        achievement_icon=achievement_icon_path(TOURNAMENT_CHAMPION.key),
        achievement_name=TOURNAMENT_CHAMPION.name,
        username="Reko",
    )
    image = Image.open(io.BytesIO(png))
    assert image.format == "PNG"
    assert image.size == (ACHIEVEMENT_CARD_WIDTH, ACHIEVEMENT_CARD_HEIGHT)


def test_each_dynamic_field_stays_in_its_own_place() -> None:
    """Only three things change: the badge in the circle, the name in the
    middle plate, the username in the bottom plate. The rest is artwork."""
    template = Image.open(_ACHIEVEMENT_CARD_PATH).convert("RGB")
    ring_only = _render(None, "", "")
    cx, cy = _BADGE_CENTER
    circle = (cx - 160, cy - 160, cx + 160, cy + 140)  # the circle's visible part
    assert _inside(_changed(ring_only, template), circle)

    icon = achievement_icon_path(TOURNAMENT_CHAMPION.key)
    assert _inside(_changed(_render(icon, "", ""), ring_only), circle)

    for name in ("Champion", "Veteran of a Thousand", "W" * 40):
        assert _inside(_changed(_render(None, name, ""), ring_only), _ACHIEVEMENT_NAME_BOX)
    for user in ("Reko", "gjpqy Wolf", "W" * 32):
        assert _inside(_changed(_render(None, "", user), ring_only), _ACHIEVEMENT_USER_BOX)


def test_every_achievement_has_its_own_badge() -> None:
    default = achievement_icon_path("_default")
    assert default.is_file()
    for achievement in CATALOG:
        path = achievement_icon_path(achievement.key)
        assert path.is_file() and path != default, achievement.key
    assert achievement_icon_path("not_a_real_achievement") == default


def test_a_missing_icon_file_still_renders_the_card() -> None:
    card = _render(achievement_icon_path("_default").with_name("missing.png"), "Champion", "Reko")
    assert card.size == (ACHIEVEMENT_CARD_WIDTH, ACHIEVEMENT_CARD_HEIGHT)


def test_assets_ship_inside_src() -> None:
    for path in (
        _ACHIEVEMENT_CARD_PATH,
        _ACHIEVEMENT_NAME_FONT_PATH,
        achievement_icon_path("_default"),
    ):
        assert path.exists()
        assert "src" in path.parts and "web" not in path.parts


def test_the_congratulations_line_pings_the_member() -> None:
    text = build_achievement_congrats(who="<@42>", achievement=TOURNAMENT_CHAMPION)
    assert text.startswith("🎉 Congratulations <@42>!")
    assert f"**{TOURNAMENT_CHAMPION.name}**" in text
    assert TOURNAMENT_CHAMPION.description in text
