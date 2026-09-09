"""Read access to the Achievement catalog (reference data, seeded by migration)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement


class AchievementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: str) -> Achievement | None:
        stmt = select(Achievement).where(Achievement.key == key)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> list[Achievement]:
        return list((await self._session.execute(select(Achievement))).scalars().all())
