"""The Featured Player (docs/DECISIONS.md ADR-111): staff's /feature pick,
shown on the website's home page. Stored as a Brawlhalla account (never a
Discord id, ADR-040) that BRAWLISTAN already tracks, so its numbers are real.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.guild_settings_repository import GuildSettingsRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from services.report_service import clean_text

MAX_NOTE = 140


@dataclass(frozen=True)
class FeaturedPlayer:
    player: BrawlhallaPlayer
    note: str | None
    featured_at: datetime
    latest: RankingSnapshot | None


class FeaturedService:
    def __init__(self, session: AsyncSession) -> None:
        self._settings = GuildSettingsRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._audit = AuditLogRepository(session)

    async def set(
        self,
        *,
        guild_id: int,
        brawlhalla_id: int,
        note: str | None,
        staff_discord_id: int,
        now: datetime | None = None,
    ) -> BrawlhallaPlayer:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_id)
        if player is None:
            raise NotFoundError(
                "That player isn't tracked by BRAWLISTAN yet — they need to be on the "
                "rankings (/link or /pakistan add) before they can be featured."
            )
        cleaned = clean_text(note, limit=MAX_NOTE) if note else None
        await self._settings.set_featured(
            guild_id, brawlhalla_id=brawlhalla_id, note=cleaned or None, at=now or datetime.now(UTC)
        )
        await self._audit.add(
            guild_id=guild_id,
            action="feature.set",
            source="discord",
            actor_discord_id=staff_discord_id,
            subject=f"{player.player_name} ({brawlhalla_id})",
        )
        return player

    async def clear(self, *, guild_id: int, staff_discord_id: int) -> None:
        await self._settings.set_featured(guild_id, brawlhalla_id=None, note=None, at=None)
        await self._audit.add(
            guild_id=guild_id,
            action="feature.clear",
            source="discord",
            actor_discord_id=staff_discord_id,
            subject="featured player cleared",
        )

    async def current(self, guild_id: int) -> FeaturedPlayer | None:
        settings = await self._settings.get(guild_id)
        if settings is None or settings.featured_brawlhalla_id is None:
            return None
        player = await self._players.get_by_brawlhalla_id(settings.featured_brawlhalla_id)
        if player is None or settings.featured_at is None:
            return None
        return FeaturedPlayer(
            player=player,
            note=settings.featured_note,
            featured_at=settings.featured_at,
            latest=await self._ranking.get_latest(player.id),
        )
