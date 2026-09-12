"""API-facing response models.

Kept separate from the internal ORM/domain models — the same
API-change-resilience principle docs/BRAWLHALLA_API.md applies to the
Brawlhalla integration applies here too: what the API promises callers
shouldn't be coupled 1:1 to internal schema.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ClanInfoResponse(BaseModel):
    name: str
    motto: str
    tagline: str
    member_count: int


class LeaderboardEntryResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None


class RosterEntryResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None
    member_since: datetime | None


class AchievementResponse(BaseModel):
    key: str
    name: str
    description: str
    awarded_at: datetime


class AchievementGalleryEntryResponse(BaseModel):
    key: str
    name: str
    description: str
    holder_count: int
    total_members: int
    completion_pct: float


class PlayerProfileResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None
    global_rank: int | None
    achievements: list[AchievementResponse]


class RankingHistoryEntryResponse(BaseModel):
    captured_at: datetime
    rating: int | None
    peak_rating: int | None
    tier: str | None


class LegendMasteryResponse(BaseModel):
    legend_name_key: str
    games: int
    wins: int
    kos: int
    damagedealt: int
    falls: int


class MatchResultResponse(BaseModel):
    kind: str
    opponents: list[str]
    won: bool
    confirmed_at: datetime


class TournamentSummaryResponse(BaseModel):
    id: int
    name: str
    kind: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None


class BracketEntrantResponse(BaseModel):
    id: int
    seed: int | None
    names: list[str]
    eliminated: bool


class BracketMatchResponse(BaseModel):
    round_number: int
    slot_index: int
    entrant_a: BracketEntrantResponse | None
    entrant_b: BracketEntrantResponse | None
    winner_entrant_id: int | None
    status: str


class TournamentBracketResponse(BaseModel):
    tournament: TournamentSummaryResponse
    entrants: list[BracketEntrantResponse]
    matches: list[BracketMatchResponse]


class CommunityActivityEntryResponse(BaseModel):
    player_name: str
    level: int
    rank_title: str
    xp: int
