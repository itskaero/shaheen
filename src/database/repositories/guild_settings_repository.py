"""Persistence for GuildSettings — setup mode and the last announced season."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.guild_settings import GuildSettings


class GuildSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, guild_id: int) -> GuildSettings | None:
        return await self._session.get(GuildSettings, guild_id)

    async def set_mode(self, guild_id: int, mode: str) -> GuildSettings:
        settings = await self.get(guild_id)
        now = datetime.now(UTC)
        if settings is not None:
            settings.setup_mode = mode
            settings.last_setup_at = now
            return settings

        settings = GuildSettings(guild_id=guild_id, setup_mode=mode, last_setup_at=now)
        self._session.add(settings)
        await self._session.flush()
        return settings

    async def mark_season_announced(self, guild_id: int, brawlhalla_season: int) -> None:
        """Remember the season-start post (docs/DECISIONS.md ADR-102).

        A guild that has never run /setup has no row yet; it gets one in
        development mode, the same default /setup itself starts from.
        """
        settings = await self.get(guild_id)
        if settings is None:
            settings = GuildSettings(guild_id=guild_id, setup_mode="development")
            self._session.add(settings)
        settings.announced_season = brawlhalla_season
        await self._session.flush()
