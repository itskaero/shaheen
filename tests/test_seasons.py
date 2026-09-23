"""Pakistan Seasons over Brawlhalla's (docs/DECISIONS.md ADR-102)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.seasons import (
    ANCHOR_START,
    SEASON_LENGTH,
    SEASONS,
    brawlhalla_season_at,
    pakistan_season,
    season_label,
    season_to_announce,
)


def test_s42_starts_at_the_anchor_and_lasts_13_weeks() -> None:
    assert brawlhalla_season_at(ANCHOR_START) == 42
    assert brawlhalla_season_at(ANCHOR_START + SEASON_LENGTH - timedelta(seconds=1)) == 42
    assert brawlhalla_season_at(ANCHOR_START + SEASON_LENGTH) == 43
    assert brawlhalla_season_at(ANCHOR_START - timedelta(seconds=1)) == 41


def test_the_override_wins_over_the_calendar() -> None:
    assert brawlhalla_season_at(ANCHOR_START, override=44) == 44


def test_s42_is_pakistan_season_one() -> None:
    season = pakistan_season(42)
    assert season is not None
    assert (season.number, season.name, season.name_urdu, season.badge) == (
        1,
        "Zarb-e-Shaheen",
        "ضربِ شاہین",
        "01",
    )
    assert season.starts_at == ANCHOR_START
    assert season.ends_at == datetime(2026, 12, 23, tzinfo=UTC)


def test_every_badge_is_used_once_then_the_names_cycle() -> None:
    names = [pakistan_season(42 + i).name for i in range(len(SEASONS))]  # type: ignore[union-attr]
    assert names == [name for name, _urdu in SEASONS]
    fourteenth = pakistan_season(42 + len(SEASONS))
    assert fourteenth is not None
    assert (fourteenth.number, fourteenth.name, fourteenth.badge) == (14, "Zarb-e-Shaheen", "01")


def test_seasons_before_s42_have_no_pakistan_season() -> None:
    assert pakistan_season(41) is None
    assert pakistan_season(None) is None


def test_labels() -> None:
    assert season_label(43) == "Pakistan Season 2 · Sarfaroshi · Brawlhalla S43"
    assert season_label(41) == "Brawlhalla Season 41"
    assert season_label(None) is None


def test_season_to_announce() -> None:
    first = season_to_announce(42, None)
    assert first is not None and first.number == 1
    assert season_to_announce(42, 42) is None
    later = season_to_announce(43, 42)
    assert later is not None and later.name == "Sarfaroshi"
    assert season_to_announce(41, None) is None  # nothing to announce before S42
