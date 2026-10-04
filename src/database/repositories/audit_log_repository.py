"""Persistence for AuditLogEntry — append-only (docs/DECISIONS.md ADR-107)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.audit_log import AuditLogEntry


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        guild_id: int,
        action: str,
        source: str,
        subject: str,
        actor_discord_id: int | None = None,
        detail: dict[str, object] | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            guild_id=guild_id,
            action=action,
            source=source,
            subject=subject[:160],
            actor_discord_id=actor_discord_id,
            detail=detail,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_recent(self, guild_id: int, *, limit: int = 50) -> list[AuditLogEntry]:
        stmt = (
            select(AuditLogEntry)
            .where(AuditLogEntry.guild_id == guild_id)
            .order_by(AuditLogEntry.id.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
