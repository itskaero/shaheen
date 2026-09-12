"""Read-only lookups behind /profile, /rank, /stats, /legends.

Reuses LinkService for "which player is this Discord member linked to" so
that query lives in one place. Translates Brawlhalla failures into
core.exceptions the same way LinkService does. /profile also folds in
chat-gamification standing and earned achievements (docs/DECISIONS.md
ADR-067) — both already tracked elsewhere in the system, just never
surfaced on the one-look card before now.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import IntegrationError
from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.chat_activity import ChatActivity
from database.models.shaheen_member import ShaheenMember
from database.repositories.chat_activity_repository import ChatActivityRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from integrations.brawlhalla.errors import BrawlhallaAPIError
from integrations.brawlhalla.models import PlayerRankedResponse, PlayerStatsResponse
from integrations.brawlhalla.service import BrawlhallaService
from services.link_service import LinkService


class ProfileService:
    def __init__(
        self, session: AsyncSession, link_service: LinkService, brawlhalla: BrawlhallaService
    ) -> None:
        self._links = link_service
        self._brawlhalla = brawlhalla
        self._chat_activity = ChatActivityRepository(session)
        self._achievements = MemberAchievementRepository(session)

    async def get_linked_player(
        self, *, guild_id: int, discord_id: int
    ) -> tuple[ShaheenMember, BrawlhallaPlayer] | None:
        return await self._links.get_active_link(guild_id=guild_id, discord_id=discord_id)

    async def get_stats(self, brawlhalla_id: int) -> PlayerStatsResponse:
        try:
            return await self._brawlhalla.get_stats(brawlhalla_id)
        except BrawlhallaAPIError as exc:
            raise IntegrationError(
                "Brawlhalla is not responding right now. Try again shortly."
            ) from exc

    async def get_ranked(self, brawlhalla_id: int) -> PlayerRankedResponse | None:
        try:
            return await self._brawlhalla.get_ranked(brawlhalla_id)
        except BrawlhallaAPIError as exc:
            raise IntegrationError(
                "Brawlhalla is not responding right now. Try again shortly."
            ) from exc

    async def get_chat_activity(self, *, guild_id: int, discord_id: int) -> ChatActivity | None:
        return await self._chat_activity.get(guild_id=guild_id, discord_id=discord_id)

    async def get_achievements(
        self, shaheen_member_id: int
    ) -> list[tuple[Achievement, datetime]]:
        return await self._achievements.list_with_details(shaheen_member_id)
