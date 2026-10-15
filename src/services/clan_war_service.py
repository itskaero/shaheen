"""Clan Wars over the database (docs/DECISIONS.md ADR-131).

The rules are in services/clan_wars.py. This scores a week from the ranking
snapshots, records each finished week once, and builds the board the bot,
the API and the website show. Discord-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.clan_war_result import ClanWarResult
from database.models.team import Team
from database.repositories.clan_war_repository import ClanWarRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.team_repository import TeamRepository
from services.clan_wars import TEAM_TOP_N, player_points, season_table, team_points
from services.quests import baseline, week_bounds


@dataclass(frozen=True)
class MemberScore:
    player: BrawlhallaPlayer
    points: int


@dataclass
class TeamWeek:
    team: Team
    points: int
    # Members who scored this week, best first; the first TEAM_TOP_N count.
    scorers: list[MemberScore] = field(default_factory=list)

    @property
    def counted(self) -> list[MemberScore]:
        return self.scorers[:TEAM_TOP_N]


@dataclass
class WarWeek:
    season: int | None
    week_start: date
    ends_at: datetime
    standings: list[TeamWeek] = field(default_factory=list)


@dataclass(frozen=True)
class SeasonRow:
    team: Team
    wins: int
    points: int
    weeks: int


@dataclass(frozen=True)
class LastWinner:
    team: Team
    points: int
    week_start: date


@dataclass
class ClanWarsBoard:
    week: WarWeek
    season_table: list[SeasonRow]
    last_winner: LastWinner | None


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)  # SQLite drops the zone


class ClanWarService:
    def __init__(self, session: AsyncSession) -> None:
        self._teams = TeamRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._results = ClanWarRepository(session)

    async def week(self, guild_id: int, *, now: datetime | None = None) -> WarWeek:
        """The war week `now` falls in, scored up to `now`."""
        now = now or datetime.now(UTC)
        monday, start, end = week_bounds(now)
        return await self._score(guild_id, monday, start, min(now, end), end)

    async def board(self, guild_id: int, *, now: datetime | None = None) -> ClanWarsBoard:
        now = now or datetime.now(UTC)
        week = await self.week(guild_id, now=now)
        season = week.season if week.season is not None else await self._ranking.current_season()
        teams = {t.id: t for t in await self._teams.list_for_guild(guild_id)}
        rows: list[SeasonRow] = []
        last: LastWinner | None = None
        if season is not None:
            results = await self._results.for_season(guild_id, season)
            for record in season_table([(r.team_id, r.points, r.place) for r in results]):
                if record.team_id in teams:
                    rows.append(
                        SeasonRow(teams[record.team_id], record.wins, record.points, record.weeks)
                    )
            winner = next((r for r in results if r.place == 1 and r.team_id in teams), None)
            if winner is not None:
                last = LastWinner(teams[winner.team_id], winner.points, winner.week_start)
        return ClanWarsBoard(week=week, season_table=rows, last_winner=last)

    async def record_finished(
        self, guild_id: int, *, now: datetime | None = None
    ) -> list[ClanWarResult]:
        """Keep last week's standings if they aren't kept yet. Idempotent: a
        week is recorded once. A week nobody scored in records nothing."""
        now = now or datetime.now(UTC)
        monday, start, end = week_bounds(now - timedelta(days=7))
        if await self._results.week_recorded(guild_id, monday):
            return []
        week = await self._score(guild_id, monday, start, end, end)
        scored = [t for t in week.standings if t.points > 0]
        if week.season is None or not scored:
            return []
        results = [
            ClanWarResult(
                guild_id=guild_id,
                team_id=t.team.id,
                season=week.season,
                week_start=monday,
                points=t.points,
                place=place,
                recorded_at=now,
            )
            for place, t in enumerate(scored, start=1)
        ]
        await self._results.add_all(results)
        return results

    # --- internals -----------------------------------------------------------

    async def _score(
        self, guild_id: int, monday: date, start: datetime, until: datetime, end: datetime
    ) -> WarWeek:
        """Every team's points from readings in [start, until)."""
        # The week's own season: a season that began after it doesn't count.
        season = await self._ranking.season_before(until)
        week = WarWeek(season=season, week_start=monday, ends_at=end)
        for team in await self._teams.list_for_guild(guild_id):
            scorers = []
            if season is not None:
                for _member, player in await self._teams.active_members(team.id):
                    points = await self._member_points(player, season, start, until)
                    if points > 0:
                        scorers.append(MemberScore(player, points))
            scorers.sort(key=lambda s: (-s.points, s.player.player_name.lower()))
            week.standings.append(
                TeamWeek(team=team, points=team_points(s.points for s in scorers), scorers=scorers)
            )
        week.standings.sort(key=lambda t: (-t.points, t.team.name.lower()))
        return week

    async def _member_points(
        self, player: BrawlhallaPlayer, season: int, start: datetime, until: datetime
    ) -> int:
        before = await self._ranking.latest_before(player.id, start, season=season)
        this_week = [
            s
            for s in await self._ranking.list_since(player.id, start)
            if s.season == season and _aware(s.captured_at) < until
        ]
        readings = ([before] if before else []) + this_week
        first = baseline(readings, week_start=start, season=season)
        latest = this_week[-1] if this_week else None
        return player_points(first, latest)
