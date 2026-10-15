"""Pakistani cities for City Wars (docs/DECISIONS.md ADR-128).

A fixed list, so the city board compares like with like and nobody can type
an arbitrary label onto a public page. The twin cities share one entry.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

CITIES: dict[str, str] = {
    "karachi": "Karachi",
    "lahore": "Lahore",
    "islamabad": "Islamabad / Rawalpindi",
    "faisalabad": "Faisalabad",
    "multan": "Multan",
    "peshawar": "Peshawar",
    "quetta": "Quetta",
    "hyderabad": "Hyderabad",
    "sialkot": "Sialkot",
    "gujranwala": "Gujranwala",
    "bahawalpur": "Bahawalpur",
    "sukkur": "Sukkur",
    "abbottabad": "Abbottabad",
    "mardan": "Mardan",
    "sargodha": "Sargodha",
    "azad-kashmir": "Azad Kashmir",
    "gilgit-baltistan": "Gilgit-Baltistan",
}

# The city score is the average of its best this-many placed players, so a
# city with one star and a city with many players compete fairly.
CITY_TOP_N = 5


def city_label(key: str | None) -> str | None:
    return CITIES.get(key) if key else None


@dataclass
class CityStanding:
    key: str
    label: str
    rating: int  # average of the top CITY_TOP_N placed ratings
    players: int  # placed players from the city
    top: list[tuple[str, int]] = field(default_factory=list)  # (player name, rating), best first


def city_standings(placed: Sequence[tuple[str | None, str, int]]) -> list[CityStanding]:
    """(city, player name, rating) for every placed player -> cities, best
    first. Players without a city are left out; a city needs one placed
    player to appear."""
    by_city: dict[str, list[tuple[str, int]]] = {}
    for city, name, rating in placed:
        if city in CITIES:
            by_city.setdefault(city, []).append((name, rating))
    standings = []
    for key, players in by_city.items():
        players.sort(key=lambda p: p[1], reverse=True)
        best = players[:CITY_TOP_N]
        standings.append(
            CityStanding(
                key=key,
                label=CITIES[key],
                rating=round(sum(r for _n, r in best) / len(best)),
                players=len(players),
                top=best,
            )
        )
    standings.sort(key=lambda c: (-c.rating, -c.players, c.label))
    return standings
