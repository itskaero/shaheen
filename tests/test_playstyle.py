"""services/playstyle.py — derived, not Brawlhalla-reported, tags
(docs/DECISIONS.md ADR-094).
"""

from __future__ import annotations

from dataclasses import dataclass

from services.playstyle import derive_playstyle_tags


@dataclass
class _Legend:
    games: int = 0
    kos: int = 0
    damagedealt: int = 0
    falls: int = 0


def test_empty_legends_falls_back_to_well_rounded() -> None:
    assert derive_playstyle_tags([]) == ["Well-Rounded"]


def test_zero_games_falls_back_without_dividing_by_zero() -> None:
    legends = [_Legend(games=0, kos=5, damagedealt=1000, falls=0)]
    assert derive_playstyle_tags(legends) == ["Well-Rounded"]


def test_high_kos_rate_is_aggressive() -> None:
    legends = [_Legend(games=10, kos=15, damagedealt=1000, falls=15)]
    assert "Aggressive" in derive_playstyle_tags(legends)


def test_high_damage_rate_is_heavy_hitter() -> None:
    legends = [_Legend(games=10, kos=2, damagedealt=8000, falls=15)]
    assert "Heavy Hitter" in derive_playstyle_tags(legends)


def test_low_falls_rate_is_survivor() -> None:
    legends = [_Legend(games=10, kos=2, damagedealt=1000, falls=5)]
    assert "Survivor" in derive_playstyle_tags(legends)


def test_middling_stats_fall_back_to_well_rounded() -> None:
    legends = [_Legend(games=10, kos=5, damagedealt=3000, falls=15)]
    assert derive_playstyle_tags(legends) == ["Well-Rounded"]


def test_multiple_tags_can_fire_together_in_a_stable_order() -> None:
    legends = [_Legend(games=10, kos=15, damagedealt=8000, falls=5)]
    assert derive_playstyle_tags(legends) == ["Aggressive", "Heavy Hitter", "Survivor"]


def test_aggregates_across_multiple_legends() -> None:
    legends = [
        _Legend(games=5, kos=10, damagedealt=1000, falls=10),
        _Legend(games=5, kos=10, damagedealt=1000, falls=10),
    ]
    # 20 kos / 10 games = 2.0 kos/game -> Aggressive
    assert "Aggressive" in derive_playstyle_tags(legends)
