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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


def fix_name(name: str) -> str:
    """The API sends UTF-8 names that arrive read as Latin-1 ("WÃLF" for
    "WØLF"). Undo that when it is what happened; leave anything else alone."""
    try:
        return name.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


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

    @field_validator("name")
    @classmethod
    def _fix_name(cls, value: str) -> str:
        return fix_name(value)

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


class RankedTeamStat(_RankedStanding):
    """One 2v2 team in PlayerRankedResponse.teams_2v2 (docs/DECISIONS.md ADR-105).

    `teamname` is Brawlhalla's "PlayerOne+PlayerTwo" label.
    """

    model_config = ConfigDict(extra="ignore")

    brawlhalla_id_one: int
    brawlhalla_id_two: int
    teamname: str = ""
    region: str | None = None
    global_rank: int | None = None
    wins: int = 0
    games: int = 0

    def partner_name(self, brawlhalla_id: int) -> str | None:
        """The other player's name, from the "One+Two" team label."""
        one, sep, two = self.teamname.partition("+")
        if not sep:
            return None
        return two if brawlhalla_id == self.brawlhalla_id_one else one


class PlayerRankedResponse(_RankedStanding):
    """GET /player/{id}/ranked — current 1v1 ranked standing. 404 if unranked."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    brawlhalla_id: int
    name: str
    region: str | None = None
    global_rank: int | None = None
    region_rank: int | None = None
    wins: int = 0
    games: int = 0
    legends: list[RankedLegendStat] = Field(default_factory=list)
    # The API's key is "2v2", which isn't a Python identifier.
    teams_2v2: list[RankedTeamStat] = Field(default_factory=list, alias="2v2")

    @property
    def best_2v2(self) -> RankedTeamStat | None:
        """The player's highest-rated placed 2v2 team this season, if any."""
        placed = [team for team in self.teams_2v2 if team.rating is not None]
        return max(placed, key=lambda team: team.rating or 0, default=None)

    @model_validator(mode="after")
    def _unranked_positions_are_none(self) -> Self:
        if self.global_rank is not None and self.global_rank <= 0:
            self.global_rank = None
        if self.region_rank is not None and self.region_rank <= 0:
            self.region_rank = None
        return self


class ClanMember(BaseModel):
    """One member of GET /clan/{id} (ADR-120)."""

    model_config = ConfigDict(extra="ignore")

    brawlhalla_id: int
    name: str
    rank: str = "Member"  # Leader | Officer | Member | Recruit
    join_date: int | None = None
    xp: int = 0

    @field_validator("name")
    @classmethod
    def _fix_name(cls, value: str) -> str:
        return fix_name(value)


class ClanResponse(BaseModel):
    """GET /clan/{id}: the clan and its members (ADR-120)."""

    model_config = ConfigDict(extra="ignore")

    clan_id: int
    clan_name: str
    members: list[ClanMember] = Field(default_factory=list, alias="clan")

    @field_validator("clan_name")
    @classmethod
    def _fix_clan_name(cls, value: str) -> str:
        return fix_name(value)
