"""Pakistan Seasons — Shaheen's own named seasons over Brawlhalla's
(docs/DECISIONS.md ADR-102).

Pure: no Discord, no database. Brawlhalla S42 (which began 2026-09-23) is
Pakistan Season 1, and every Brawlhalla season after it is the next
Pakistan season. Brawlhalla's API never says which season a response
belongs to, so the current season is derived from the date: the anchor
plus one season per 13 weeks, Brawlhalla's usual length. When their real
dates drift, `BRAWLHALLA_SEASON` overrides the calculation.

Names and art (web/assets/img/seasons/, src/assets/img/seasons/) come from
the owner's BRAWLISTAN season cards (ADR-108), in the order printed on them:
Markhor is Season 1. Numbers keep counting past 13; the names cycle, so
Pakistan Season 14 is Markhor again.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

ANCHOR_BRAWLHALLA_SEASON = 42
ANCHOR_START = datetime(2026, 9, 23, tzinfo=UTC)
SEASON_LENGTH = timedelta(weeks=13)

# (English, Urdu), in card order 01..13 — spelled as on the cards, except
# the Season 2 card's "SHAHEN" typo (ADR-108).
SEASONS: tuple[tuple[str, str], ...] = (
    ("Markhor", "مارخور"),
    ("Zarb-e-Shaheen", "ضربِ شاہین"),
    ("Sarfaroshi", "سرفروشی"),
    ("Chogori", "چوگوری"),
    ("Sindhu Dhaara", "سندھ دھارا"),
    ("Panchnad", "پنجند"),
    ("Shimsal", "شمشال"),
    ("Rang-e-Thar", "رنگِ تھر"),
    ("Gwadar", "گوادر"),
    ("Namak Koh", "نمک کوہ"),
    ("Baad-e-Saawan", "بادِ ساون"),
    ("Margallah", "مارگلہ"),
    ("Nayi Subah", "نئی صبح"),
)


@dataclass(frozen=True)
class PakistanSeason:
    number: int
    brawlhalla_season: int
    name: str
    name_urdu: str
    badge: str  # "01".."13" — the season card's file stem
    # The 13-week window from the anchor. Approximate: Brawlhalla's real
    # reset can land a few days either side.
    starts_at: datetime
    ends_at: datetime


def brawlhalla_season_at(now: datetime, *, override: int | None = None) -> int:
    """The Brawlhalla season in progress at `now` (override wins when set).

    Before the anchor this counts backwards the same way, so it never
    returns something newer than the anchor for an older date.
    """
    if override is not None:
        return override
    return ANCHOR_BRAWLHALLA_SEASON + (now - ANCHOR_START) // SEASON_LENGTH


def pakistan_season(brawlhalla_season: int | None) -> PakistanSeason | None:
    """The Pakistan season for a Brawlhalla season, or None before S42."""
    if brawlhalla_season is None or brawlhalla_season < ANCHOR_BRAWLHALLA_SEASON:
        return None
    offset = brawlhalla_season - ANCHOR_BRAWLHALLA_SEASON
    name, name_urdu = SEASONS[offset % len(SEASONS)]
    starts_at = ANCHOR_START + offset * SEASON_LENGTH
    return PakistanSeason(
        number=offset + 1,
        brawlhalla_season=brawlhalla_season,
        name=name,
        name_urdu=name_urdu,
        badge=f"{offset % len(SEASONS) + 1:02d}",
        starts_at=starts_at,
        ends_at=starts_at + SEASON_LENGTH,
    )


def season_label(brawlhalla_season: int | None) -> str | None:
    """The one wording for a season, shared by every Discord surface."""
    if brawlhalla_season is None:
        return None
    season = pakistan_season(brawlhalla_season)
    if season is None:
        return f"Brawlhalla Season {brawlhalla_season}"
    return f"Pakistan Season {season.number} · {season.name} · Brawlhalla S{brawlhalla_season}"


def season_to_announce(current: int, last_announced: int | None) -> PakistanSeason | None:
    """The season to announce now, if `current` hasn't been announced yet."""
    if last_announced is not None and current <= last_announced:
        return None
    return pakistan_season(current)
