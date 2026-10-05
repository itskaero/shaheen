"""API-facing response models.

Kept separate from the internal ORM/domain models — the same
API-change-resilience principle docs/BRAWLHALLA_API.md applies to the
Brawlhalla integration applies here too: what the API promises callers
shouldn't be coupled 1:1 to internal schema.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from services.seasons import pakistan_season


class PakistanSeasonResponse(BaseModel):
    """Shaheen's named season over a Brawlhalla one (docs/DECISIONS.md ADR-102).

    `badge` is the image stem — web/assets/img/seasons/<badge>.webp.
    """

    number: int
    brawlhalla_season: int
    name: str
    name_urdu: str
    badge: str
    starts_at: datetime
    ends_at: datetime

    @classmethod
    def for_brawlhalla_season(cls, season: int | None) -> PakistanSeasonResponse | None:
        found = pakistan_season(season)
        if found is None:
            return None
        return cls(
            number=found.number,
            brawlhalla_season=found.brawlhalla_season,
            name=found.name,
            name_urdu=found.name_urdu,
            badge=found.badge,
            starts_at=found.starts_at,
            ends_at=found.ends_at,
        )


class ClanInfoResponse(BaseModel):
    name: str
    motto: str
    tagline: str
    member_count: int
    # The Brawlhalla season every ranking view is scoped to (ADR-088).
    season: int | None
    # Its Pakistan season, None before S42 (ADR-102).
    pakistan_season: PakistanSeasonResponse | None
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


class RankingRowResponse(BaseModel):
    """One player on the Rankings page (ADR-105). Brawlhalla identity only."""

    brawlhalla_id: int
    player_name: str
    country: str
    team: str | None
    team_slug: str | None = None
    team_tag: str | None = None
    is_claimed: bool
    # Staff confirmed the account owner (/verify, ADR-107). A boolean only.
    is_verified: bool
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None
    wins: int
    games: int
    global_rank: int | None
    region_rank: int | None
    rating_2v2: int | None
    peak_rating_2v2: int | None
    tier_2v2: str | None
    partner_2v2: str | None
    trend: int | None
    main_legend: str | None


class RankingsBoardResponse(BaseModel):
    season: int | None
    pakistan_season: PakistanSeasonResponse | None
    seasons: list[int]
    rows: list[RankingRowResponse]


class PlayerDirectoryEntryResponse(BaseModel):
    """One tracked player on the Players page (ADR-106). Brawlhalla identity only."""

    brawlhalla_id: int
    slug: str
    player_name: str
    country: str | None
    team: str | None
    team_slug: str | None = None
    team_tag: str | None = None
    is_claimed: bool
    is_verified: bool
    on_pakistan_board: bool
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None
    main_legend: str | None


class SeasonSummaryResponse(BaseModel):
    season: int
    pakistan_season_number: int | None
    pakistan_season_name: str | None
    final_rating: int | None
    peak_rating: int | None
    readings: int


class RisingPlayerResponse(BaseModel):
    """A climber on the Pakistan board over the last few days (ADR-104)."""

    brawlhalla_id: int
    player_name: str
    rating: int
    rating_gain: int
    is_claimed: bool


class LegendMetaResponse(BaseModel):
    legend_name_key: str
    player_count: int
    total_games: int
    win_rate: float


class FeaturedPlayerResponse(BaseModel):
    """Staff's /feature pick (ADR-111). Brawlhalla identity only (ADR-040)."""

    brawlhalla_id: int
    player_name: str
    note: str | None
    featured_at: datetime
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
    pakistan_season: PakistanSeasonResponse | None
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


class SeasonCardResponse(BaseModel):
    """One Pakistan season on the Seasons page (ADR-113)."""

    season: PakistanSeasonResponse
    status: str  # "past" | "current" | "upcoming"
    has_data: bool
    champion: str | None


class SeasonRiserResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    rating_gain: int
    rating: int


class SeasonLegendResponse(BaseModel):
    legend_name_key: str
    games: int
    win_rate: float
    players: int


class SeasonDetailResponse(BaseModel):
    """A season's story (ADR-113). Every part is null/empty without data."""

    season: PakistanSeasonResponse
    status: str
    has_data: bool
    top: list[RankingRowResponse]
    rising: SeasonRiserResponse | None
    legend: SeasonLegendResponse | None
    tournaments: list[TournamentSummaryResponse]


class TeamPlayerResponse(BaseModel):
    """A player on a team (ADR-114). Brawlhalla identity only (ADR-040)."""

    brawlhalla_id: int
    player_name: str
    slug: str
    role: str  # "captain" | "player"
    # In-game clan rank (Leader, Officer, Member, Recruit) for a clan-synced
    # player; null for one added by hand (ADR-120).
    clan_rank: str | None = None
    rating: int | None
    peak_rating: int | None
    tier: str | None
    main_legend: str | None


class TeamSummaryResponse(BaseModel):
    slug: str
    name: str
    tag: str
    country: str
    logo: str | None
    description: str | None
    is_founding: bool
    # #rrggbb or null (the BRAWLISTAN defaults); they tint the holographic card.
    accent: str | None = None
    accent_secondary: str | None = None
    # Position among teams with a team rating; null when the team has none.
    rank: int | None = None
    # The in-game Brawlhalla clan the roster mirrors (ADR-120).
    brawlhalla_clan_id: int | None = None
    members: int
    # Average of the best 3 placed players; null when nobody's placed.
    rating: int | None
    best: TeamPlayerResponse | None


class TeamAchievementResponse(BaseModel):
    player_name: str
    key: str
    name: str
    awarded_at: datetime


class TeamSeasonResponse(BaseModel):
    season: int
    pakistan_season: PakistanSeasonResponse | None
    best: int | None
    average: int | None
    players: int


class TeamDetailResponse(TeamSummaryResponse):
    roster: list[TeamPlayerResponse]
    achievements: list[TeamAchievementResponse]
    seasons: list[TeamSeasonResponse]
