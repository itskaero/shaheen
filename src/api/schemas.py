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
    # The Brawlhalla season every ranking view is scoped to (ADR-088).
    season: int | None
    discord_member_count: int | None
    discord_boost_tier: int | None
    discord_boost_count: int | None


class LeaderboardEntryResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None


class PakistanLeaderboardEntryResponse(LeaderboardEntryResponse):
    is_clan_member: bool
    # Claimed via /pakistan join by a server member (ADR-100) — a boolean
    # only, never which Discord account (ADR-040).
    is_claimed: bool


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


class AchievementHolderResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    earned_at: datetime


class AchievementGalleryEntryResponse(BaseModel):
    key: str
    name: str
    description: str
    category: str
    holder_count: int
    total_members: int
    completion_pct: float
    rarity: str
    # Earliest first — the first entry is who got there first (ADR-100).
    holders: list[AchievementHolderResponse] = []


class AchievementChecklistEntryResponse(BaseModel):
    """One catalog achievement for one player — the per-member view the
    clan-wide gallery can't give (docs/DECISIONS.md ADR-081).
    """

    key: str
    name: str
    description: str
    category: str
    earned: bool
    awarded_at: datetime | None
    # What earned it — {"games": 1043}, {"tournament_id": 3, "placement": 1}.
    # Recorded on every award since ADR-081 and read by nothing until now.
    context: dict[str, object] | None


class PlayerProfileResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None
    global_rank: int | None
    # Stored since ADR-081, exposed here as of ADR-088.
    region_rank: int | None
    season: int | None
    achievements: list[AchievementResponse]
    # A derived label, not a Brawlhalla-reported stat — see
    # services/playstyle.py (docs/DECISIONS.md ADR-096).
    playstyle_tags: list[str]


class RankingHistoryEntryResponse(BaseModel):
    captured_at: datetime
    # Brawlhalla wipes ratings between seasons (docs/DECISIONS.md ADR-088),
    # so the chart marks where one ended rather than drawing a cliff.
    season: int | None
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


class ClanMatchEntryResponse(BaseModel):
    """A confirmed clan match for the public activity feed (ADR-088)."""

    kind: str
    winners: list[str]
    losers: list[str]
    confirmed_at: datetime


class CommunityActivityEntryResponse(BaseModel):
    player_name: str
    level: int
    rank_title: str
    xp: int
