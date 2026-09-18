"""Awarding achievements — the one place that turns AchievementDefs into rows.

Discord-agnostic (docs/ARCHITECTURE.md): it persists awards and returns
what was newly granted; callers decide whether to announce.

Before ADR-081 this logic was copy-pasted into services/link_service.py
and services/snapshot_service.py, and the four new award sources added in
that round would have made it six copies. It lives here once instead, so
every source — ranked snapshots, clan matches, tournaments, chat levels,
MVP weeks, tenure — awards the same way and records the same context.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.member_achievement import MemberAchievement
from database.repositories.achievement_repository import AchievementRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from services.achievements import AchievementDef

logger = logging.getLogger(__name__)


class AchievementService:
    def __init__(self, session: AsyncSession) -> None:
        self._catalog = AchievementRepository(session)
        self._awards = MemberAchievementRepository(session)

    async def earned_keys(self, shaheen_member_id: int) -> set[str]:
        return await self._awards.list_earned_keys(shaheen_member_id)

    async def award(
        self,
        *,
        shaheen_member_id: int,
        definition: AchievementDef,
        extra: dict[str, object] | None = None,
    ) -> MemberAchievement | None:
        """Grant one achievement. None if already held or not in the catalog.

        `extra` records *what* earned it — the games count, the tournament
        id, the peak rating. It's stored on the award row so two members
        holding the same badge still read differently (ADR-081); before
        this round the column existed but nothing ever wrote to it.
        """
        catalog_row = await self._catalog.get_by_key(definition.key)
        if catalog_row is None:
            # Catalog rows come from migrations, so a miss means the deploy
            # is mid-migration. Never block the caller's real work over it.
            logger.warning(
                "Achievement %r missing from the catalog — run migrations?", definition.key
            )
            return None
        return await self._awards.award(
            shaheen_member_id=shaheen_member_id,
            achievement_id=catalog_row.id,
            extra=extra,
        )

    async def award_many(
        self,
        *,
        shaheen_member_id: int,
        definitions: tuple[AchievementDef, ...],
        extra: dict[str, object] | None = None,
    ) -> list[AchievementDef]:
        """Grant several at once; returns only the ones actually newly granted."""
        granted: list[AchievementDef] = []
        for definition in definitions:
            if (
                await self.award(
                    shaheen_member_id=shaheen_member_id, definition=definition, extra=extra
                )
                is not None
            ):
                granted.append(definition)
        return granted
