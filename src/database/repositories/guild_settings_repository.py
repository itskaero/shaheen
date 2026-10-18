"""Persistence for GuildSettings — setup mode, the last announced season and
the featured player."""

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

    async def _get_or_create(self, guild_id: int) -> GuildSettings:
        settings = await self.get(guild_id)
        if settings is None:
            settings = GuildSettings(guild_id=guild_id, setup_mode="development")
            self._session.add(settings)
        return settings

    async def set_featured(
        self, guild_id: int, *, brawlhalla_id: int | None, note: str | None, at: datetime | None
    ) -> None:
        """Set or (with brawlhalla_id=None) clear the featured player (ADR-111)."""
        settings = await self._get_or_create(guild_id)
        settings.featured_brawlhalla_id = brawlhalla_id
        settings.featured_note = note
        settings.featured_at = at
        await self._session.flush()

    async def set_access(
        self,
        guild_id: int,
        *,
        join_role_id: int | None,
        approved_role_id: int | None,
        approval_enabled: bool,
    ) -> GuildSettings:
        """Store the join-access settings (ADR-123)."""
        settings = await self._get_or_create(guild_id)
        settings.join_role_id = join_role_id
        settings.approved_role_id = approved_role_id
        settings.approval_enabled = approval_enabled
        await self._session.flush()
        return settings

    async def set_coaching(
        self, guild_id: int, *, coach_role_id: int | None, coaching_channel_id: int | None
    ) -> GuildSettings:
        """Store the Coach role and the coaching channel (ADR-126)."""
        settings = await self._get_or_create(guild_id)
        settings.coach_role_id = coach_role_id
        settings.coaching_channel_id = coaching_channel_id
        await self._session.flush()
        return settings

    async def set_war_room(
        self, guild_id: int, *, channel_id: int | None, message_id: int | None = None
    ) -> GuildSettings:
        """Point the war room at a channel (ADR-136), or with None turn it off."""
        settings = await self._get_or_create(guild_id)
        settings.war_room_channel_id = channel_id
        settings.war_room_message_id = message_id
        await self._session.flush()
        return settings

    async def set_spar_ping(
        self, guild_id: int, *, role_id: int | None = None, last_ping_at: datetime | None = None
    ) -> GuildSettings:
        """Remember the Spar Ping role and/or when it was last pinged (ADR-136)."""
        settings = await self._get_or_create(guild_id)
        if role_id is not None:
            settings.spar_role_id = role_id
        if last_ping_at is not None:
            settings.spar_last_ping_at = last_ping_at
        await self._session.flush()
        return settings

    async def mark_season_announced(self, guild_id: int, brawlhalla_season: int) -> None:
        """Remember the season-start post (docs/DECISIONS.md ADR-102).

        A guild that has never run /setup has no row yet; it gets one in
        development mode, the same default /setup itself starts from.
        """
        settings = await self._get_or_create(guild_id)
        settings.announced_season = brawlhalla_season
        await self._session.flush()
