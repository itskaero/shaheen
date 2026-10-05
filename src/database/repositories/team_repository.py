"""Persistence for Team and TeamMember (docs/DECISIONS.md ADR-114)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.team import Team, TeamMember


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, team: Team) -> Team:
        self._session.add(team)
        await self._session.flush()
        return team

    async def get_by_slug(self, guild_id: int, slug: str) -> Team | None:
        stmt = select(Team).where(Team.guild_id == guild_id, Team.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def find(self, guild_id: int, name_or_slug: str) -> Team | None:
        """By slug, name or tag, ignoring case — what /team options accept."""
        needle = name_or_slug.strip().lower()
        stmt = select(Team).where(
            Team.guild_id == guild_id,
            (Team.slug == needle)
            | (func.lower(Team.name) == needle)
            | (func.lower(Team.tag) == needle),
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def list_for_guild(self, guild_id: int) -> list[Team]:
        stmt = select(Team).where(Team.guild_id == guild_id).order_by(Team.id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def active_members(self, team_id: int) -> list[tuple[TeamMember, BrawlhallaPlayer]]:
        stmt = (
            select(TeamMember, BrawlhallaPlayer)
            .join(BrawlhallaPlayer, BrawlhallaPlayer.id == TeamMember.brawlhalla_player_id)
            .where(TeamMember.team_id == team_id, TeamMember.left_at.is_(None))
            .order_by(TeamMember.joined_at)
        )
        return [(m, p) for m, p in (await self._session.execute(stmt)).all()]

    async def active_membership(self, player_id: int) -> tuple[TeamMember, Team] | None:
        stmt = (
            select(TeamMember, Team)
            .join(Team, Team.id == TeamMember.team_id)
            .where(TeamMember.brawlhalla_player_id == player_id, TeamMember.left_at.is_(None))
        )
        row = (await self._session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def teams_of(self, guild_id: int, player_ids: Iterable[int]) -> dict[int, Team]:
        """Internal player id -> active team, for every player that has one."""
        return {
            pid: team
            for pid, (team, _member) in (await self.memberships_of(guild_id, player_ids)).items()
        }

    async def memberships_of(
        self, guild_id: int, player_ids: Iterable[int]
    ) -> dict[int, tuple[Team, TeamMember]]:
        """Internal player id -> (active team, membership), one query."""
        ids = list(player_ids)
        if not ids:
            return {}
        stmt = (
            select(TeamMember, Team)
            .join(Team, Team.id == TeamMember.team_id)
            .where(
                Team.guild_id == guild_id,
                TeamMember.left_at.is_(None),
                TeamMember.brawlhalla_player_id.in_(ids),
            )
        )
        return {
            member.brawlhalla_player_id: (team, member)
            for member, team in (await self._session.execute(stmt)).all()
        }

    async def add_member(
        self,
        *,
        team_id: int,
        player_id: int,
        role: str,
        joined_at: datetime,
        source: str = "manual",
        clan_rank: str | None = None,
    ) -> TeamMember:
        member = TeamMember(
            team_id=team_id,
            brawlhalla_player_id=player_id,
            role=role,
            joined_at=joined_at,
            source=source,
            clan_rank=clan_rank,
        )
        self._session.add(member)
        await self._session.flush()
        return member

    async def active_player_ids(self, guild_id: int, *, country: str | None = None) -> set[int]:
        """Internal player ids on any team in this guild: tracked players
        (ADR-120). `country` keeps only teams from that country (ADR-125)."""
        stmt = (
            select(TeamMember.brawlhalla_player_id)
            .join(Team, Team.id == TeamMember.team_id)
            .where(Team.guild_id == guild_id, TeamMember.left_at.is_(None))
        )
        if country is not None:
            stmt = stmt.where(Team.country == country)
        return set((await self._session.execute(stmt)).scalars().all())

    async def with_clans(self, guild_id: int) -> list[Team]:
        stmt = select(Team).where(Team.guild_id == guild_id, Team.brawlhalla_clan_id.is_not(None))
        return list((await self._session.execute(stmt)).scalars().all())

    async def close(self, member: TeamMember, at: datetime) -> None:
        member.left_at = at
        await self._session.flush()
