"""Persistence for membership applications (docs/DECISIONS.md ADR-089)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.application import Application, ApplicationStatus


class ApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, application: Application) -> Application:
        self._session.add(application)
        await self._session.flush()
        return application

    async def get(self, application_id: int) -> Application | None:
        return await self._session.get(Application, application_id)

    async def get_pending(self, *, guild_id: int, discord_id: int) -> Application | None:
        stmt = select(Application).where(
            Application.guild_id == guild_id,
            Application.discord_id == discord_id,
            Application.status == ApplicationStatus.PENDING,
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def get_latest(self, *, guild_id: int, discord_id: int) -> Application | None:
        """Most recent application of any status — powers /apply's cooldown
        check and the applicant-facing status reply.
        """
        stmt = (
            select(Application)
            .where(Application.guild_id == guild_id, Application.discord_id == discord_id)
            .order_by(Application.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def get_by_review_message(self, message_id: int) -> Application | None:
        """The application a review card belongs to.

        The Approve/Deny buttons look themselves up this way so their
        custom_ids can stay static and survive a restart — see
        bot/views/application.py.
        """
        stmt = select(Application).where(Application.review_message_id == message_id)
        return (await self._session.execute(stmt)).scalars().first()

    async def list_pending(self, guild_id: int, *, limit: int = 25) -> list[Application]:
        stmt = (
            select(Application)
            .where(
                Application.guild_id == guild_id,
                Application.status == ApplicationStatus.PENDING,
            )
            .order_by(Application.created_at.asc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_for_member(self, *, guild_id: int, discord_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(Application.guild_id == guild_id, Application.discord_id == discord_id)
        )
        return (await self._session.execute(stmt)).scalar_one()
