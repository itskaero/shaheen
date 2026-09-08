"""Persistence for MemberAchievement — awards, at most once per member+achievement."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.member_achievement import MemberAchievement


class MemberAchievementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has(self, *, shaheen_member_id: int, achievement_id: int) -> bool:
        stmt = select(MemberAchievement.id).where(
            MemberAchievement.shaheen_member_id == shaheen_member_id,
            MemberAchievement.achievement_id == achievement_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def award(
        self, *, shaheen_member_id: int, achievement_id: int, extra: dict[str, object] | None = None
    ) -> MemberAchievement | None:
        """Grants the achievement, or returns None if already held."""
        if await self.has(shaheen_member_id=shaheen_member_id, achievement_id=achievement_id):
            return None

        award = MemberAchievement(
            shaheen_member_id=shaheen_member_id,
            achievement_id=achievement_id,
            awarded_at=datetime.now(UTC),
            extra=extra,
        )
        self._session.add(award)
        await self._session.flush()
        return award

    async def list_for_member(self, shaheen_member_id: int) -> list[MemberAchievement]:
        stmt = select(MemberAchievement).where(
            MemberAchievement.shaheen_member_id == shaheen_member_id
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_earned_keys(self, shaheen_member_id: int) -> set[str]:
        stmt = (
            select(Achievement.key)
            .join(MemberAchievement, MemberAchievement.achievement_id == Achievement.id)
            .where(MemberAchievement.shaheen_member_id == shaheen_member_id)
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def list_with_details(self, shaheen_member_id: int) -> list[tuple[Achievement, datetime]]:
        stmt = (
            select(Achievement, MemberAchievement.awarded_at)
            .join(MemberAchievement, MemberAchievement.achievement_id == Achievement.id)
            .where(MemberAchievement.shaheen_member_id == shaheen_member_id)
            .order_by(MemberAchievement.awarded_at.asc())
        )
        result = await self._session.execute(stmt)
        return [(achievement, awarded_at) for achievement, awarded_at in result]
