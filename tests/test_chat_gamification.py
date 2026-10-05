"""Pure XP/level curve + rank titles (docs/DECISIONS.md ADR-065).

No DB, no Discord — just the math and the ladder.
"""

from __future__ import annotations

from services.chat_gamification import (
    RANK_TITLES,
    level_for_xp,
    rank_title_for_level,
    roll_message_xp,
    xp_for_level,
)


def test_level_for_xp_at_zero_and_negative_is_one() -> None:
    assert level_for_xp(0) == 1
    assert level_for_xp(-100) == 1


def test_xp_for_level_at_one_and_below_is_zero() -> None:
    assert xp_for_level(1) == 0
    assert xp_for_level(0) == 0


def test_documented_thresholds() -> None:
    # docs/DECISIONS.md ADR-065: level 2 at 100xp, level 3 at 400xp,
    # level 10 at 8,100xp.
    assert xp_for_level(2) == 100
    assert xp_for_level(3) == 400
    assert xp_for_level(10) == 8100

    assert level_for_xp(100) == 2
    assert level_for_xp(400) == 3
    assert level_for_xp(8100) == 10


def test_level_for_xp_just_below_threshold_is_previous_level() -> None:
    assert level_for_xp(xp_for_level(2) - 1) == 1
    assert level_for_xp(xp_for_level(3) - 1) == 2
    assert level_for_xp(xp_for_level(10) - 1) == 9


def test_curve_is_exact_inverse_pair() -> None:
    for level in range(1, 51):
        threshold = xp_for_level(level)
        assert level_for_xp(threshold) == level


def test_level_for_xp_is_monotonic_non_decreasing() -> None:
    previous = level_for_xp(0)
    for xp in range(0, 20_000, 37):
        current = level_for_xp(xp)
        assert current >= previous
        previous = current


def test_rank_titles_are_sorted_ascending_by_min_level() -> None:
    min_levels = [rank.min_level for rank in RANK_TITLES]
    assert min_levels == sorted(min_levels)


def test_rank_title_for_level_below_first_rank_is_lowest() -> None:
    assert rank_title_for_level(1) == "Hatchling"


def test_rank_title_for_level_matches_documented_ladder() -> None:
    assert rank_title_for_level(1) == "Hatchling"
    assert rank_title_for_level(4) == "Hatchling"
    assert rank_title_for_level(5) == "Brawler"
    assert rank_title_for_level(9) == "Brawler"
    assert rank_title_for_level(10) == "Warrior"
    assert rank_title_for_level(15) == "Veteran"
    assert rank_title_for_level(20) == "Elite"
    assert rank_title_for_level(25) == "Legend"
    assert rank_title_for_level(30) == "Valhallan"
    assert rank_title_for_level(999) == "Valhallan"


def test_roll_message_xp_stays_in_documented_range() -> None:
    rolls = {roll_message_xp() for _ in range(500)}
    assert rolls <= set(range(5, 16))
    assert min(rolls) >= 5
    assert max(rolls) <= 15
