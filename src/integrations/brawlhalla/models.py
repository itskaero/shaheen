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

from pydantic import BaseModel, ConfigDict, Field


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


class RankedLegendStat(BaseModel):
    """One entry in PlayerRankedResponse.legends — ranked stats for one Legend."""

    model_config = ConfigDict(extra="ignore")

    legend_id: int
    legend_name_key: str
    rating: int | None = None
    peak_rating: int | None = None
    tier: str | None = None
    wins: int = 0
    games: int = 0


class PlayerRankedResponse(BaseModel):
    """GET /player/{id}/ranked — current 1v1 ranked standing. 404 if unranked."""

    model_config = ConfigDict(extra="ignore")

    brawlhalla_id: int
    name: str
    region: str | None = None
    global_rank: int | None = None
    region_rank: int | None = None
    rating: int | None = None
    peak_rating: int | None = None
    tier: str | None = None
    wins: int = 0
    games: int = 0
    legends: list[RankedLegendStat] = Field(default_factory=list)
