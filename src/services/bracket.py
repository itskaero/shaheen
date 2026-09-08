"""Pure single-elimination bracket logic (docs/DECISIONS.md ADR-035).

No Discord or database dependency — `generate_bracket()` takes an entrant
count and returns round-1 pairings (with byes resolved) plus the total
round count; `next_slot()` maps a completed bracket slot to where its
winner plugs in next. services/tournament_service.py is the only caller,
and owns all persistence. Seeding is by registration order (seed 1 = first
registrant) — there is no Elo/skill-based seeding yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["a", "b"]


def next_power_of_two(n: int) -> int:
    power = 1
    while power < n:
        power *= 2
    return power


def seeding_order(bracket_size: int) -> list[int]:
    """Standard single-elimination seeding order for a power-of-two bracket.

    e.g. size 4 -> [1, 4, 2, 3] (seed 1 vs 4, seed 2 vs 3), so top seeds
    can only meet in later rounds.
    """
    if bracket_size < 1 or bracket_size & (bracket_size - 1) != 0:
        raise ValueError(f"bracket_size must be a power of two, got {bracket_size}")

    order = [1]
    while len(order) < bracket_size:
        size = len(order) * 2
        order = [value for seed in order for value in (seed, size + 1 - seed)]
    return order


@dataclass(frozen=True)
class RoundOneSlot:
    slot_index: int
    entrant_a_seed: int | None
    entrant_b_seed: int | None
    bye_winner_seed: int | None  # set when exactly one of the above is None


@dataclass(frozen=True)
class BracketPlan:
    entrant_count: int
    bracket_size: int
    total_rounds: int
    round_one: tuple[RoundOneSlot, ...]


def generate_bracket(entrant_count: int) -> BracketPlan:
    """Round 1 pairings (byes pre-resolved) for `entrant_count` seeded entrants.

    Seed 1 is the first registrant, seed 2 the second, and so on. Later
    rounds are left for the caller to build as empty slots — see
    `next_slot()`.
    """
    if entrant_count < 2:
        raise ValueError("A tournament needs at least 2 entrants")

    bracket_size = next_power_of_two(entrant_count)
    order = seeding_order(bracket_size)
    total_rounds = bracket_size.bit_length() - 1

    round_one = []
    for slot_index in range(bracket_size // 2):
        seed_a = order[slot_index * 2]
        seed_b = order[slot_index * 2 + 1]
        a = seed_a if seed_a <= entrant_count else None
        b = seed_b if seed_b <= entrant_count else None
        bye_winner = a if b is None else (b if a is None else None)
        round_one.append(RoundOneSlot(slot_index, a, b, bye_winner))

    return BracketPlan(
        entrant_count=entrant_count,
        bracket_size=bracket_size,
        total_rounds=total_rounds,
        round_one=tuple(round_one),
    )


def next_slot(round_number: int, slot_index: int) -> tuple[int, int, Side]:
    """Where a slot's winner plugs into the next round.

    Returns (next_round_number, next_slot_index, side) — `side` is which
    half of the next slot this winner fills.
    """
    return round_number + 1, slot_index // 2, "a" if slot_index % 2 == 0 else "b"
