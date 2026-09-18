"""Pure achievement evaluation logic — docs/DECISIONS.md ADR-030/ADR-031."""

from __future__ import annotations

from services.achievements import (
    CATALOG,
    CHAT_LEVEL_10,
    CHAT_LEVEL_25,
    CHAT_LEVEL_50,
    FIRST_WIN,
    GAMES_100,
    GAMES_500,
    GLOBAL_TOP_1000,
    MIN_RANKED_GAMES_FOR_WIN_RATE,
    MVP_OF_WEEK,
    PEAK_1500,
    PEAK_1800,
    PEAK_2000,
    REGION_TOP_100,
    SCRIM_REGULAR,
    TIER_DIAMOND_PLUS,
    TIER_PLATINUM,
    TOURNAMENT_CHAMPION,
    TOURNAMENT_ENTRANT,
    TOURNAMENT_FINALIST,
    VETERAN_30D,
    VETERAN_365D,
    WIN_RATE_60,
    WINS_10,
    WINS_50,
    evaluate_competition_achievements,
    evaluate_engagement_achievements,
    evaluate_snapshot_achievements,
    evaluate_tenure_achievements,
    rarity_label,
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


# --- ADR-081: the expanded catalog and its new evaluators -------------------


def test_peak_rating_thresholds_are_inclusive_at_the_boundary() -> None:
    earned = evaluate_snapshot_achievements(
        games=0, ranked_tier=None, already_earned=set(), peak_rating=1800
    )
    assert PEAK_1500 in earned
    assert PEAK_1800 in earned
    assert PEAK_2000 not in earned


def test_peak_rating_one_below_a_threshold_does_not_award_it() -> None:
    earned = evaluate_snapshot_achievements(
        games=0, ranked_tier=None, already_earned=set(), peak_rating=1799
    )
    assert PEAK_1500 in earned
    assert PEAK_1800 not in earned


def test_global_and_region_standing_award_at_their_cutoffs() -> None:
    earned = evaluate_snapshot_achievements(
        games=0, ranked_tier=None, already_earned=set(), global_rank=1000, region_rank=100
    )
    assert GLOBAL_TOP_1000 in earned
    assert REGION_TOP_100 in earned


def test_standing_just_outside_the_cutoffs_awards_nothing() -> None:
    earned = evaluate_snapshot_achievements(
        games=0, ranked_tier=None, already_earned=set(), global_rank=1001, region_rank=101
    )
    assert GLOBAL_TOP_1000 not in earned
    assert REGION_TOP_100 not in earned


def test_win_rate_needs_the_minimum_games_floor() -> None:
    """A 100% win rate over 3 games is noise, not a 60%-win-rate achievement."""
    earned = evaluate_snapshot_achievements(
        games=0, ranked_tier=None, already_earned=set(), ranked_wins=3, ranked_games=3
    )
    assert WIN_RATE_60 not in earned


def test_win_rate_awards_once_over_the_games_floor() -> None:
    earned = evaluate_snapshot_achievements(
        games=0,
        ranked_tier=None,
        already_earned=set(),
        ranked_wins=30,
        ranked_games=MIN_RANKED_GAMES_FOR_WIN_RATE,
    )
    assert WIN_RATE_60 in earned


def test_missing_ranked_data_awards_nothing_ranked() -> None:
    """An unranked player still snapshots — the ranked fields are just None."""
    earned = evaluate_snapshot_achievements(games=120, ranked_tier=None, already_earned=set())
    assert earned == (GAMES_100,)


def test_competition_match_win_thresholds() -> None:
    earned = evaluate_competition_achievements(already_earned=set(), match_wins=10)
    assert FIRST_WIN in earned
    assert WINS_10 in earned
    assert WINS_50 not in earned


def test_competition_tournament_events_are_independent() -> None:
    earned = evaluate_competition_achievements(
        already_earned=set(), tournaments_entered=1, tournament_finals=1, tournament_wins=1
    )
    assert TOURNAMENT_ENTRANT in earned
    assert TOURNAMENT_FINALIST in earned
    assert TOURNAMENT_CHAMPION in earned


def test_competition_scrim_regular_needs_ten_signups() -> None:
    assert SCRIM_REGULAR not in evaluate_competition_achievements(
        already_earned=set(), scrims_joined=9
    )
    assert SCRIM_REGULAR in evaluate_competition_achievements(
        already_earned=set(), scrims_joined=10
    )


def test_engagement_chat_levels_and_mvp() -> None:
    earned = evaluate_engagement_achievements(already_earned=set(), chat_level=25, mvp_weeks=1)
    assert CHAT_LEVEL_10 in earned
    assert CHAT_LEVEL_25 in earned
    assert CHAT_LEVEL_50 not in earned
    assert MVP_OF_WEEK in earned


def test_tenure_thresholds_and_unknown_join_date() -> None:
    assert VETERAN_30D in evaluate_tenure_achievements(days_in_clan=30, already_earned=set())
    assert VETERAN_365D not in evaluate_tenure_achievements(days_in_clan=364, already_earned=set())
    # joined_at is nullable; tenure simply doesn't evaluate rather than guessing.
    assert evaluate_tenure_achievements(days_in_clan=None, already_earned=set()) == ()


def test_every_evaluator_respects_already_earned() -> None:
    assert (
        evaluate_competition_achievements(already_earned={"first_win", "wins_10"}, match_wins=10)
        == ()
    )
    assert evaluate_engagement_achievements(already_earned={"chat_level_10"}, chat_level=10) == ()
    assert evaluate_tenure_achievements(days_in_clan=40, already_earned={"veteran_30d"}) == ()


def test_catalog_keys_are_unique_and_categorised() -> None:
    keys = [definition.key for definition in CATALOG]
    assert len(keys) == len(set(keys))
    assert all(definition.category for definition in CATALOG)


def test_rarity_label_bands() -> None:
    assert rarity_label(0) == "Unclaimed"
    assert rarity_label(5) == "Legendary"
    assert rarity_label(10) == "Rare"
    assert rarity_label(25) == "Uncommon"
    assert rarity_label(80) == "Common"
