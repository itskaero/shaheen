"""Parsing of Brawlhalla API response shapes into typed models."""

from __future__ import annotations

from integrations.brawlhalla.models import (
    PlayerRankedResponse,
    PlayerStatsResponse,
    SearchResult,
)


def test_search_result_parses_minimal_shape() -> None:
    result = SearchResult.model_validate({"brawlhalla_id": 42, "name": "Foo"})
    assert result.brawlhalla_id == 42
    assert result.name == "Foo"


def test_player_stats_parses_legends_and_ignores_unknown_fields() -> None:
    raw = {
        "brawlhalla_id": 123,
        "name": "Foo",
        "xp": 1000,
        "level": 12,
        "games": 50,
        "wins": 30,
        "some_future_field": "unrelated",
        "legends": [
            {
                "legend_id": 1,
                "legend_name_key": "bodvar",
                "games": 10,
                "wins": 6,
                "damagedealt": 5000,
                "kos": 20,
                "unknown_legend_field": True,
            }
        ],
    }
    stats = PlayerStatsResponse.model_validate(raw)
    assert stats.games == 50
    assert stats.wins == 30
    assert len(stats.legends) == 1
    assert stats.legends[0].legend_name_key == "bodvar"
    assert stats.legends[0].kos == 20


def test_player_ranked_handles_missing_optional_fields() -> None:
    raw = {"brawlhalla_id": 7, "name": "Unranked"}
    ranked = PlayerRankedResponse.model_validate(raw)
    assert ranked.tier is None
    assert ranked.rating is None
    assert ranked.legends == []


def test_player_ranked_parses_full_shape() -> None:
    raw = {
        "brawlhalla_id": 7,
        "name": "Ranked",
        "region": "us-e",
        "global_rank": 100,
        "region_rank": 10,
        "rating": 1800,
        "peak_rating": 1900,
        "tier": "Diamond III",
        "wins": 40,
        "games": 70,
        "legends": [
            {
                "legend_id": 2,
                "legend_name_key": "cassidy",
                "rating": 1700,
                "peak_rating": 1750,
                "tier": "Platinum I",
                "wins": 10,
                "games": 18,
            }
        ],
    }
    ranked = PlayerRankedResponse.model_validate(raw)
    assert ranked.tier == "Diamond III"
    assert ranked.region == "us-e"
    assert ranked.legends[0].legend_name_key == "cassidy"


def test_player_ranked_after_a_season_reset_reads_as_unplaced() -> None:
    """The API answers 200 with zeros and tier "None" for a player with no
    placement games this season — not a real rating (ADR-101).
    """
    raw = {
        "brawlhalla_id": 7,
        "name": "Reset",
        "region": "ME",
        "rating": 0,
        "peak_rating": 0,
        "tier": "None",
        "global_rank": 0,
        "region_rank": 0,
        "wins": 0,
        "games": 0,
        "legends": [
            {"legend_id": 2, "legend_name_key": "cassidy", "rating": 0, "tier": "None"},
        ],
    }
    ranked = PlayerRankedResponse.model_validate(raw)
    assert (ranked.rating, ranked.peak_rating, ranked.tier) == (None, None, None)
    assert (ranked.global_rank, ranked.region_rank) == (None, None)
    assert (ranked.legends[0].rating, ranked.legends[0].tier) == (None, None)
    assert ranked.region == "ME"


def test_unplaced_this_season_keeps_a_real_peak() -> None:
    ranked = PlayerRankedResponse.model_validate(
        {"brawlhalla_id": 7, "name": "X", "rating": 0, "peak_rating": 1906, "tier": "none"}
    )
    assert (ranked.rating, ranked.tier, ranked.peak_rating) == (None, None, 1906)
