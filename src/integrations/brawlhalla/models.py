"""Response models for the Brawlhalla API.

Kept separate from internal database/domain models (database/models/) per
docs/BRAWLHALLA_API.md's API-change resilience requirement: parsing lives
here, internal models live there, and nothing outside this integration
depends on the exact shape of the external API.

Field names were verified against a community-maintained mirror of the
official Python client (see docs/DECISIONS.md ADR-022) rather than the
live docs, which were unreachable from this environment — re-verify
against https://dev.brawlhalla.com/ if fields ever look wrong at runtime.
`extra="ignore"` on every model means an API field we don't model yet is
silently dropped instead of breaking parsing.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# What the API reports for a player (or a Legend) with no placement games
# in the current ranked season — e.g. everyone right after a season reset:
# a 200 with rating/peak 0 and tier "None", rather than the 404 an account
# that never played ranked gets. Normalized to "no rating" here so nothing
# downstream shows a 0 rating or a "None" tier (docs/DECISIONS.md ADR-101).
_UNPLACED_TIERS = frozenset({"", "none", "unranked"})


class _RankedStanding(BaseModel):
    rating: int | None = None
    peak_rating: int | None = None
    tier: str | None = None

    @model_validator(mode="after")
    def _unplaced_is_none(self) -> Self:
        unplaced = (self.tier is not None and self.tier.strip().lower() in _UNPLACED_TIERS) or (
            self.rating is not None and self.rating <= 0
        )
        if unplaced:
            self.rating = None
            self.tier = None
        if self.peak_rating is not None and self.peak_rating <= 0:
            self.peak_rating = None
        return self


class SearchResult(BaseModel):
    """GET /search?steamid=... — a Steam account resolved to a Brawlhalla ID."""

    model_config = ConfigDict(extra="ignore")

    brawlhalla_id: int
    name: str


class LegendStat(BaseModel):
    """One entry in PlayerStatsResponse.legends — lifetime stats for one Legend."""

    model_config = ConfigDict(extra="ignore")

    legend_id: int
    legend_name_key: str
    games: int = 0
    wins: int = 0
    damagedealt: int = 0
    damagetaken: int = 0
    kos: int = 0
    falls: int = 0
    suicides: int = 0
    teamkos: int = 0


class PlayerStatsResponse(BaseModel):
    """GET /player/{id}/stats — lifetime, non-ranked-specific player stats."""

    model_config = ConfigDict(extra="ignore")

    brawlhalla_id: int
    name: str
    xp: int = 0
    level: int = 1
    games: int = 0
    wins: int = 0
    legends: list[LegendStat] = Field(default_factory=list)


class RankedLegendStat(_RankedStanding):
    """One entry in PlayerRankedResponse.legends — ranked stats for one Legend."""

    model_config = ConfigDict(extra="ignore")

    legend_id: int
    legend_name_key: str
    wins: int = 0
    games: int = 0


class PlayerRankedResponse(_RankedStanding):
    """GET /player/{id}/ranked — current 1v1 ranked standing. 404 if unranked."""

    model_config = ConfigDict(extra="ignore")

    brawlhalla_id: int
    name: str
    region: str | None = None
    global_rank: int | None = None
    region_rank: int | None = None
    wins: int = 0
    games: int = 0
    legends: list[RankedLegendStat] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unranked_positions_are_none(self) -> Self:
        if self.global_rank is not None and self.global_rank <= 0:
            self.global_rank = None
        if self.region_rank is not None and self.region_rank <= 0:
            self.region_rank = None
        return self
