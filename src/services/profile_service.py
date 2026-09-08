"""Read-only lookups behind /profile, /rank, /stats, /legends.

Reuses LinkService for "which player is this Discord member linked to" so
that query lives in one place. Translates Brawlhalla failures into
core.exceptions the same way LinkService does.
"""

from __future__ import annotations

from core.exceptions import IntegrationError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.shaheen_member import ShaheenMember
from integrations.brawlhalla.errors import BrawlhallaAPIError
from integrations.brawlhalla.models import PlayerRankedResponse, PlayerStatsResponse
from integrations.brawlhalla.service import BrawlhallaService
from services.link_service import LinkService


class ProfileService:
    def __init__(self, link_service: LinkService, brawlhalla: BrawlhallaService) -> None:
        self._links = link_service
        self._brawlhalla = brawlhalla

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
