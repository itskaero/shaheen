"""Clan Wars over the database (docs/DECISIONS.md ADR-131, ADR-136).

The rules are in services/clan_wars.py. This scores a week from the ranking
snapshots, locks each week's rosters, records each finished week once, and
builds the board the bot, the API and the website show: standings, this
week's duels, the MVP, and the season table with duel records.
Discord-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.clan_war_result import ClanWarResult
from database.models.clan_war_roster import ClanWarRoster
from database.models.team import Team
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.clan_war_repository import ClanWarRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.team_repository import TeamRepository
from services.clan_wars import (
    MIN_GAMES,
    TEAM_TOP_N,
    DuelRecord,
    DuelResult,
    duel_pairs,
    duel_records,
    duel_results,
    eligible,
    player_points,
    season_table,
    team_points,
)
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
    # Members whose points don't count (an account too new, ADR-136).
    ineligible: list[MemberScore] = field(default_factory=list)

    @property
    def counted(self) -> list[MemberScore]:
        return self.scorers[:TEAM_TOP_N]


@dataclass(frozen=True)
class Mvp:
    player: BrawlhallaPlayer
    points: int
    team: Team | None


@dataclass
class WarWeek:
    season: int | None
    week_start: date
    ends_at: datetime
    standings: list[TeamWeek] = field(default_factory=list)
    duels: list[DuelResult] = field(default_factory=list)
    roster_locked: bool = False

    @property
    def mvp(self) -> Mvp | None:
        """The week's top counted scorer, from any team."""
        best: Mvp | None = None
        for team_week in self.standings:
            for score in team_week.counted:
                if best is None or score.points > best.points:
                    best = Mvp(score.player, score.points, team_week.team)
        return best

    def team(self, team_id: int) -> TeamWeek | None:
        return next((t for t in self.standings if t.team.id == team_id), None)


@dataclass(frozen=True)
class SeasonRow:
    team: Team
    wins: int
    points: int
    weeks: int
    duels: DuelRecord = DuelRecord()


@dataclass(frozen=True)
class LastWinner:
    team: Team
    points: int
    week_start: date
    mvp: Mvp | None = None


@dataclass
class ClanWarsBoard:
    week: WarWeek
    season_table: list[SeasonRow]
    last_winner: LastWinner | None


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)  # SQLite drops the zone


class ClanWarService:
    def __init__(self, session: AsyncSession, *, min_games: int = MIN_GAMES) -> None:
        self._teams = TeamRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._results = ClanWarRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._min_games = min_games

    async def week(self, guild_id: int, *, now: datetime | None = None) -> WarWeek:
        """The war week `now` falls in, scored up to `now`."""
        now = now or datetime.now(UTC)
        monday, start, end = week_bounds(now)
        return await self._score(guild_id, monday, start, min(now, end), end)

    async def lock_roster(self, guild_id: int, *, now: datetime | None = None) -> int:
        """Lock this week's rosters if they aren't yet: every active team
        member, each on one team. Idempotent; returns the players locked."""
        now = now or datetime.now(UTC)
        monday, _start, _end = week_bounds(now)
        if await self._results.roster_locked(guild_id, monday):
            return 0
        rows: list[ClanWarRoster] = []
        seen: set[int] = set()
        for team in sorted(await self._teams.list_for_guild(guild_id), key=lambda t: t.id):
            for _member, player in await self._teams.active_members(team.id):
                if player.id in seen:
                    continue
                seen.add(player.id)
                rows.append(
                    ClanWarRoster(
                        guild_id=guild_id,
                        week_start=monday,
                        team_id=team.id,
                        brawlhalla_player_id=player.id,
                    )
                )
        if rows:
            await self._results.add_roster(rows)
        return len(rows)

    async def board(self, guild_id: int, *, now: datetime | None = None) -> ClanWarsBoard:
        now = now or datetime.now(UTC)
        week = await self.week(guild_id, now=now)
        season = week.season if week.season is not None else await self._ranking.current_season()
        teams = {t.id: t for t in await self._teams.list_for_guild(guild_id)}
        rows: list[SeasonRow] = []
        last: LastWinner | None = None
        if season is not None:
            results = await self._results.for_season(guild_id, season)
            records = duel_records(self._recorded_duels(results, list(teams)))
            for record in season_table([(r.team_id, r.points, r.place) for r in results]):
                if record.team_id in teams:
                    rows.append(
                        SeasonRow(
                            teams[record.team_id],
                            record.wins,
                            record.points,
                            record.weeks,
                            records.get(record.team_id, DuelRecord()),
                        )
                    )
            winner = next((r for r in results if r.place == 1 and r.team_id in teams), None)
            if winner is not None:
                last = LastWinner(
                    teams[winner.team_id],
                    winner.points,
                    winner.week_start,
                    await self._stored_mvp(winner),
                )
        return ClanWarsBoard(week=week, season_table=rows, last_winner=last)

    async def finished_week(self, guild_id: int, *, now: datetime | None = None) -> WarWeek:
        """Last week, scored in full (for the Monday verdict)."""
        now = now or datetime.now(UTC)
        monday, start, end = week_bounds(now - timedelta(days=7))
        return await self._score(guild_id, monday, start, end, end)

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
        mvp = week.mvp
        results = [
            ClanWarResult(
                guild_id=guild_id,
                team_id=t.team.id,
                season=week.season,
                week_start=monday,
                points=t.points,
                place=place,
                recorded_at=now,
                mvp_brawlhalla_player_id=mvp.player.id if mvp else None,
                mvp_points=mvp.points if mvp else None,
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
        locked = await self._results.roster(guild_id, monday)
        teams = await self._teams.list_for_guild(guild_id)
        week = WarWeek(season=season, week_start=monday, ends_at=end, roster_locked=bool(locked))
        for team in teams:
            if locked:
                players = locked.get(team.id, [])
            else:
                players = [player for _member, player in await self._teams.active_members(team.id)]
            scorers: list[MemberScore] = []
            ineligible: list[MemberScore] = []
            if season is not None:
                for player in players:
                    points = await self._member_points(player, season, start, until)
                    if points <= 0:
                        continue
                    before = await self._ranking.latest_before_any(player.id, start)
                    if eligible(before, self._min_games):
                        scorers.append(MemberScore(player, points))
                    else:
                        ineligible.append(MemberScore(player, points))
            scorers.sort(key=lambda s: (-s.points, s.player.player_name.lower()))
            week.standings.append(
                TeamWeek(
                    team=team,
                    points=team_points(s.points for s in scorers),
                    scorers=scorers,
                    ineligible=ineligible,
                )
            )
        week.standings.sort(key=lambda t: (-t.points, t.team.name.lower()))
        week.duels = duel_results(
            duel_pairs([t.id for t in teams], monday), {t.team.id: t.points for t in week.standings}
        )
        return week

    @staticmethod
    def _recorded_duels(
        results: list[ClanWarResult], team_ids: list[int]
    ) -> list[list[DuelResult]]:
        """Each recorded week's duels, re-paired from the current teams.
        Teams that scored nothing that week aren't recorded and count as 0."""
        by_week: dict[date, dict[int, int]] = {}
        for r in results:
            by_week.setdefault(r.week_start, {})[r.team_id] = r.points
        return [
            duel_results(duel_pairs(team_ids, monday), points) for monday, points in by_week.items()
        ]

    async def _stored_mvp(self, result: ClanWarResult) -> Mvp | None:
        if result.mvp_brawlhalla_player_id is None or result.mvp_points is None:
            return None
        player = await self._players.get_by_id(result.mvp_brawlhalla_player_id)
        if player is None:
            return None
        membership = await self._teams.active_membership(player.id)
        return Mvp(player, result.mvp_points, membership[1] if membership else None)

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
