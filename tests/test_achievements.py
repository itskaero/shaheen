"""Pure achievement evaluation logic — docs/DECISIONS.md ADR-030/ADR-031."""

from __future__ import annotations

from services.achievements import (
    GAMES_100,
    GAMES_500,
    TIER_DIAMOND_PLUS,
    TIER_PLATINUM,
    evaluate_snapshot_achievements,
    tier_at_least,
    tier_index,
)


def test_tier_index_orders_families_low_to_high() -> None:
    assert tier_index("Gold I") < tier_index("Platinum III")
    assert tier_index("Platinum I") < tier_index("Diamond I")


def test_tier_index_same_within_a_family() -> None:
    assert tier_index("Gold I") == tier_index("Gold III")


def test_tier_index_none_for_unrecognized_tier() -> None:
    assert tier_index("Some New Tier Name") is None


def test_tier_at_least_matches_exact_and_prefixed_names() -> None:
    assert tier_at_least("Platinum III", "platinum")
    assert tier_at_least("Diamond", "platinum")
    assert not tier_at_least("Gold I", "platinum")


def test_tier_at_least_fails_open_on_unrecognized_tier() -> None:
    assert not tier_at_least("Some New Tier Name", "platinum")


def test_tier_at_least_handles_none() -> None:
    assert not tier_at_least(None, "platinum")


def test_evaluate_awards_games_milestones() -> None:
    earned = evaluate_snapshot_achievements(games=150, ranked_tier=None, already_earned=set())
    assert GAMES_100 in earned
    assert GAMES_500 not in earned


def test_evaluate_awards_both_games_milestones_at_once() -> None:
    earned = evaluate_snapshot_achievements(games=600, ranked_tier=None, already_earned=set())
    assert GAMES_100 in earned
    assert GAMES_500 in earned


def test_evaluate_skips_already_earned() -> None:
    earned = evaluate_snapshot_achievements(
        games=600, ranked_tier=None, already_earned={"games_100", "games_500"}
    )
    assert earned == ()


def test_evaluate_awards_tier_achievements() -> None:
    earned = evaluate_snapshot_achievements(games=0, ranked_tier="Diamond II", already_earned=set())
    assert TIER_PLATINUM in earned
    assert TIER_DIAMOND_PLUS in earned


def test_evaluate_below_platinum_awards_nothing_tier_related() -> None:
    earned = evaluate_snapshot_achievements(games=0, ranked_tier="Gold I", already_earned=set())
    assert TIER_PLATINUM not in earned
    assert TIER_DIAMOND_PLUS not in earned
