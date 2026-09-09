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


class AchievementResponse(BaseModel):
    key: str
    name: str
    description: str
    awarded_at: datetime


class PlayerProfileResponse(BaseModel):
    brawlhalla_id: int
    player_name: str
    region: str | None
    rating: int | None
    peak_rating: int | None
    tier: str | None
    achievements: list[AchievementResponse]


class RankingHistoryEntryResponse(BaseModel):
    captured_at: datetime
    rating: int | None
    peak_rating: int | None
    tier: str | None
