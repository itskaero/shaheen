"""Persistence for GuildSettings — currently just the active setup mode."""

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
