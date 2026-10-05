"""Persistence for PlayerReport (docs/DECISIONS.md ADR-111)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.player_report import PlayerReport


class PlayerReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: PlayerReport) -> PlayerReport:
        self._session.add(report)
        await self._session.flush()
        return report

    async def get(self, report_id: int) -> PlayerReport | None:
        return await self._session.get(PlayerReport, report_id)

    async def count_by_reporter_since(
        self, guild_id: int, reporter_discord_id: int, since: datetime
    ) -> int:
        stmt = select(func.count(PlayerReport.id)).where(
            PlayerReport.guild_id == guild_id,
            PlayerReport.reporter_discord_id == reporter_discord_id,
            PlayerReport.created_at >= since,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_unposted(self, guild_id: int, *, limit: int = 20) -> list[PlayerReport]:
        """Reports with no #report embed yet — the website's, which the bot
        picks up on its tick (there's no inbound bot HTTP)."""
        stmt = (
            select(PlayerReport)
            .where(PlayerReport.guild_id == guild_id, PlayerReport.report_message_id.is_(None))
            .order_by(PlayerReport.id)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
