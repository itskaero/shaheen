"""Pure single-elimination bracket generation — docs/DECISIONS.md ADR-035."""

from __future__ import annotations

import pytest

from services.bracket import generate_bracket, next_power_of_two, next_slot, seeding_order


def test_next_power_of_two() -> None:
    assert next_power_of_two(1) == 1
    assert next_power_of_two(2) == 2
    assert next_power_of_two(3) == 4
    assert next_power_of_two(5) == 8
    assert next_power_of_two(8) == 8
    assert next_power_of_two(9) == 16


def test_seeding_order_known_values() -> None:
    assert seeding_order(1) == [1]
    assert seeding_order(2) == [1, 2]
    assert seeding_order(4) == [1, 4, 2, 3]
    assert seeding_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_seeding_order_rejects_non_power_of_two() -> None:
    with pytest.raises(ValueError):
        seeding_order(3)


def test_generate_bracket_rejects_fewer_than_two_entrants() -> None:
    with pytest.raises(ValueError):
        generate_bracket(1)


def test_generate_bracket_two_entrants_no_byes() -> None:
    plan = generate_bracket(2)
    assert plan.bracket_size == 2
    assert plan.total_rounds == 1
    (slot,) = plan.round_one
    assert (slot.entrant_a_seed, slot.entrant_b_seed) == (1, 2)
    assert slot.bye_winner_seed is None


def test_generate_bracket_power_of_two_has_no_byes() -> None:
    plan = generate_bracket(8)
    assert plan.bracket_size == 8
    assert plan.total_rounds == 3
    assert all(slot.bye_winner_seed is None for slot in plan.round_one)


def test_generate_bracket_three_entrants_gives_one_bye() -> None:
    plan = generate_bracket(3)
    assert plan.bracket_size == 4
    assert plan.total_rounds == 2
    byes = [slot for slot in plan.round_one if slot.bye_winner_seed is not None]
    assert len(byes) == 1
    assert byes[0].bye_winner_seed == 1  # top seed gets the bye


def test_generate_bracket_five_entrants_gives_three_byes() -> None:
    plan = generate_bracket(5)
    assert plan.bracket_size == 8
    byes = [slot for slot in plan.round_one if slot.bye_winner_seed is not None]
    assert len(byes) == 3
    real_matches = [slot for slot in plan.round_one if slot.bye_winner_seed is None]
    assert len(real_matches) == 1
    assert (real_matches[0].entrant_a_seed, real_matches[0].entrant_b_seed) == (4, 5)


def test_next_slot_pairs_adjacent_slots_into_one_parent() -> None:
    assert next_slot(1, 0) == (2, 0, "a")
    assert next_slot(1, 1) == (2, 0, "b")
    assert next_slot(1, 2) == (2, 1, "a")
    assert next_slot(1, 3) == (2, 1, "b")
    assert next_slot(2, 0) == (3, 0, "a")
