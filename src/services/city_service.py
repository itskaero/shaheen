"""Setting a player's city for City Wars (docs/DECISIONS.md ADR-128)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ShaheenError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.repositories.audit_log_repository import AuditLogRepository
from services.cities import CITIES


class CityService:
    def __init__(self, session: AsyncSession) -> None:
        self._audit = AuditLogRepository(session)

    async def set_city(
        self, *, guild_id: int, player: BrawlhallaPlayer, city: str | None, actor_discord_id: int
    ) -> None:
        """Set (or with None, clear) the city a player represents."""
        if city is not None and city not in CITIES:
            raise ShaheenError("Pick a city from the list.")
        player.city = city
        await self._audit.add(
            guild_id=guild_id,
            action="player.city",
            source="discord",
            actor_discord_id=actor_discord_id,
            subject=player.player_name,
            detail={"city": city},
        )
