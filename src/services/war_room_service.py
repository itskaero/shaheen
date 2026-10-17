"""The war room over the database (docs/DECISIONS.md ADR-136). Discord-free.

Gathers what the war-room channel shows (the live Clan Wars week, City Wars,
last week's result), decides what to post with services/war_room.py, keeps
the posting state in guild_settings, and awards the week's MVP.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.clan_war_repository import ClanWarRepository
from database.repositories.guild_settings_repository import GuildSettingsRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from services.achievement_service import AchievementService
from services.achievements import evaluate_engagement_achievements
from services.cities import CityStanding
from services.clan_war_service import ClanWarService, WarWeek
from services.quests import week_bounds
from services.rankings_service import RankingsService
from services.war_room import WarRoomPlan, WarRoomState, plan


@dataclass(frozen=True)
class WarRoomConfig:
    channel_id: int | None
    message_id: int | None
    state: WarRoomState


@dataclass
class WarRoomView:
    """Everything one war-room tick needs."""

    week: WarWeek
    cities: list[CityStanding]
    finished: WarWeek | None  # last week, when it's recorded
    plan: WarRoomPlan


class WarRoomService:
    def __init__(self, session: AsyncSession, *, min_games: int) -> None:
        self._settings = GuildSettingsRepository(session)
        self._results = ClanWarRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._achievements = AchievementService(session)
        self._wars = ClanWarService(session, min_games=min_games)
        self._rankings = RankingsService(session)

    async def config(self, guild_id: int) -> WarRoomConfig:
        s = await self._settings.get(guild_id)
        if s is None:
            return WarRoomConfig(None, None, WarRoomState())
        return WarRoomConfig(
            s.war_room_channel_id,
            s.war_room_message_id,
            WarRoomState(
                leader_team_id=s.war_room_leader_team_id,
                leader_week=s.war_room_leader_week,
                countdown_week=s.war_room_countdown_week,
                verdict_week=s.war_room_verdict_week,
            ),
        )

    async def set_channel(self, guild_id: int, channel_id: int | None) -> None:
        await self._settings.set_war_room(guild_id, channel_id=channel_id, message_id=None)

    async def set_message(self, guild_id: int, message_id: int | None) -> None:
        settings = await self._settings.get(guild_id)
        if settings is not None:
            settings.war_room_message_id = message_id

    async def save_state(self, guild_id: int, state: WarRoomState) -> None:
        settings = await self._settings.get(guild_id)
        if settings is None:
            return
        settings.war_room_leader_team_id = state.leader_team_id
        settings.war_room_leader_week = state.leader_week
        settings.war_room_countdown_week = state.countdown_week
        settings.war_room_verdict_week = state.verdict_week

    async def view(self, guild_id: int, *, now: datetime | None = None) -> WarRoomView:
        """Lock this week's roster, record last week if due, then score both."""
        now = now or datetime.now(UTC)
        await self._wars.lock_roster(guild_id, now=now)
        await self._wars.record_finished(guild_id, now=now)
        week = await self._wars.week(guild_id, now=now)
        last_monday, _start, _end = week_bounds(now - timedelta(days=7))
        recorded = await self._results.week_recorded(guild_id, last_monday)
        finished = await self._wars.finished_week(guild_id, now=now) if recorded else None
        _season, cities = await self._rankings.cities(guild_id)
        config = await self.config(guild_id)
        decided = plan(
            state=config.state,
            now=now,
            week_start=week.week_start,
            ends_at=week.ends_at,
            standings=[(t.team.id, t.points) for t in week.standings],
            finished_week=last_monday,
            finished_recorded=recorded,
        )
        return WarRoomView(week=week, cities=cities, finished=finished, plan=decided)

    async def award_mvp(self, guild_id: int, player_id: int) -> int | None:
        """Give the MVP achievement to a linked MVP. Returns their Discord id
        (so the verdict can mention them), or None when they aren't linked."""
        for member, player, discord_id in await self._links.list_active_for_guild(guild_id):
            if player.id != player_id:
                continue
            await self._achievements.award_many(
                shaheen_member_id=member.id,
                definitions=evaluate_engagement_achievements(
                    already_earned=await self._achievements.earned_keys(member.id), mvp_weeks=1
                ),
                extra={"awarded_for": "clan_wars_mvp"},
            )
            return discord_id
        return None
