"""Weekly quests over the database (docs/DECISIONS.md ADR-128).

The rules are in services/quests.py; this reads snapshots, records
completions (once each), and reports a player's week and season level.
Discord-free, so the API serves the same numbers the bot shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.quest_completion import QuestCompletion
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.quest_repository import QuestRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from services.quests import QUESTS, XP_PER_QUEST, Quest, baseline, level, progress, week_bounds


@dataclass(frozen=True)
class QuestProgress:
    quest: Quest
    progress: int
    done: bool


@dataclass
class QuestStatus:
    season: int | None
    week_start: date
    resets_at: datetime
    xp: int = 0
    level: int = 1
    quests: list[QuestProgress] = field(default_factory=list)


@dataclass(frozen=True)
class Completion:
    player: BrawlhallaPlayer
    quest: Quest


class QuestService:
    def __init__(self, session: AsyncSession) -> None:
        self._board = PakistanBoardRepository(session)
        self._quests = QuestRepository(session)
        self._ranking = RankingSnapshotRepository(session)

    async def status(self, player: BrawlhallaPlayer, *, now: datetime | None = None) -> QuestStatus:
        now = now or datetime.now(UTC)
        monday, _start, end = week_bounds(now)
        season = await self._ranking.current_season()
        status = QuestStatus(season=season, week_start=monday, resets_at=end)
        if season is None:
            status.quests = [QuestProgress(q, 0, False) for q in QUESTS]
            return status
        done = await self._quests.done_this_week(player.id, monday)
        values = await self._progress(player, season, now)
        status.quests = [
            QuestProgress(
                q, min(values[q.key], q.target), q.key in done or values[q.key] >= q.target
            )
            for q in QUESTS
        ]
        status.xp = await self._quests.season_count(player.id, season) * XP_PER_QUEST
        status.level = level(status.xp)
        return status

    async def evaluate(self, guild_id: int, *, now: datetime | None = None) -> list[Completion]:
        """Record the quests Pakistan-board players finished since the last
        tick. Idempotent: a quest completes once per player per week."""
        now = now or datetime.now(UTC)
        season = await self._ranking.current_season()
        if season is None:
            return []
        monday, _start, _end = week_bounds(now)
        completions = []
        for _entry, player in await self._board.list_active(guild_id):
            done = await self._quests.done_this_week(player.id, monday)
            if len(done) == len(QUESTS):
                continue
            values = await self._progress(player, season, now)
            for quest in QUESTS:
                if quest.key in done or values[quest.key] < quest.target:
                    continue
                await self._quests.add(
                    QuestCompletion(
                        brawlhalla_player_id=player.id,
                        season=season,
                        week_start=monday,
                        quest_key=quest.key,
                        completed_at=now,
                    )
                )
                completions.append(Completion(player, quest))
        return completions

    async def _progress(
        self, player: BrawlhallaPlayer, season: int, now: datetime
    ) -> dict[str, int]:
        _monday, start, _end = week_bounds(now)
        before = await self._ranking.latest_before(player.id, start, season=season)
        this_week = [
            s for s in await self._ranking.list_since(player.id, start) if s.season == season
        ]
        readings = ([before] if before else []) + this_week
        first = baseline(readings, week_start=start, season=season)
        latest = this_week[-1] if this_week else None
        return {q.key: progress(q, first, latest) for q in QUESTS}
