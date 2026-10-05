"""The Seasons page (docs/DECISIONS.md ADR-113): every Pakistan season's card,
and for one season its top 10, champion, rising player, Legend of the season
and tournaments.

Only stored readings are used. A season with no data says so rather than
showing invented numbers, and an upcoming season has a card and dates only.
No Discord here, so the website and the bot share it.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.legend_snapshot import LegendSnapshot
from database.models.tournament import Tournament
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.tournament_repository import TournamentRepository
from services.network_service import NetworkService
from services.rankings_service import RankingRow, RankingsService, ranked_rows
from services.seasons import (
    ANCHOR_BRAWLHALLA_SEASON,
    SEASONS,
    PakistanSeason,
    brawlhalla_season_at,
    pakistan_season,
)

SeasonStatus = Literal["past", "current", "upcoming"]
TOP_SIZE = 10


def _aware(value: datetime) -> datetime:
    # SQLite hands back naive datetimes; everything stored is UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def season_status(season: PakistanSeason, now: datetime) -> SeasonStatus:
    if now < season.starts_at:
        return "upcoming"
    if now >= season.ends_at:
        return "past"
    return "current"


@dataclass(frozen=True)
class LegendOfSeason:
    legend_name_key: str
    games: int
    wins: int
    players: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.games * 100 if self.games else 0.0


def legend_of_season(per_player: Iterable[Sequence[LegendSnapshot]]) -> LegendOfSeason | None:
    """The Legend with the most games played *inside* the window.

    Snapshots are lifetime totals, so a player's games in the window are
    their last reading minus their first, per Legend. A Legend nobody played
    in the window (or with a single reading) counts nothing, so a season
    without at least two readings has no Legend of the season.
    """
    games: dict[str, int] = defaultdict(int)
    wins: dict[str, int] = defaultdict(int)
    players: dict[str, int] = defaultdict(int)
    for snapshots in per_player:
        by_legend: dict[str, list[LegendSnapshot]] = defaultdict(list)
        for snap in snapshots:
            by_legend[snap.legend_name_key].append(snap)
        for key, readings in by_legend.items():
            readings.sort(key=lambda s: _aware(s.captured_at))
            played = readings[-1].games - readings[0].games
            if played <= 0:
                continue
            games[key] += played
            wins[key] += max(0, readings[-1].wins - readings[0].wins)
            players[key] += 1
    if not games:
        return None
    best = max(games, key=lambda key: (games[key], key))
    return LegendOfSeason(
        legend_name_key=best, games=games[best], wins=wins[best], players=players[best]
    )


@dataclass(frozen=True)
class SeasonCard:
    season: PakistanSeason
    status: SeasonStatus
    has_data: bool
    champion: str | None = None  # past seasons with data only


@dataclass(frozen=True)
class SeasonRiser:
    player: BrawlhallaPlayer
    rating_gain: int
    rating: int


@dataclass
class SeasonDetail:
    card: SeasonCard
    top: list[RankingRow] = field(default_factory=list)
    rising: SeasonRiser | None = None
    legend: LegendOfSeason | None = None
    tournaments: list[Tournament] = field(default_factory=list)

    @property
    def champion(self) -> RankingRow | None:
        return self.top[0] if self.top else None


class SeasonsService:
    def __init__(self, session: AsyncSession) -> None:
        self._rankings = RankingsService(session)
        self._ranking = RankingSnapshotRepository(session)
        self._board = PakistanBoardRepository(session)
        self._legends = LegendSnapshotRepository(session)
        self._network = NetworkService(session)
        self._tournaments = TournamentRepository(session)

    async def overview(self, guild_id: int, *, now: datetime | None = None) -> list[SeasonCard]:
        """Pakistan Seasons 1..max(13, current), oldest first."""
        now = now or datetime.now(UTC)
        stored = set(await self._ranking.list_seasons())
        current = brawlhalla_season_at(now)
        last = max(ANCHOR_BRAWLHALLA_SEASON + len(SEASONS) - 1, current)
        cards = []
        for brawlhalla_season in range(ANCHOR_BRAWLHALLA_SEASON, last + 1):
            season = pakistan_season(brawlhalla_season)
            assert season is not None
            status = season_status(season, now)
            has_data = brawlhalla_season in stored
            champion = None
            if status == "past" and has_data:
                top = await self._top(guild_id, brawlhalla_season)
                champion = top[0].player.player_name if top else None
            cards.append(SeasonCard(season, status, has_data, champion))
        return cards

    async def detail(
        self, guild_id: int, brawlhalla_season: int, *, now: datetime | None = None
    ) -> SeasonDetail | None:
        """None before Pakistan Season 1 (Brawlhalla S42)."""
        now = now or datetime.now(UTC)
        season = pakistan_season(brawlhalla_season)
        if season is None:
            return None
        status = season_status(season, now)
        has_data = brawlhalla_season in set(await self._ranking.list_seasons())
        detail = SeasonDetail(card=SeasonCard(season, status, has_data))
        if status == "upcoming":
            return detail

        if has_data:
            detail.top = await self._top(guild_id, brawlhalla_season)
            detail.rising = await self._rising(guild_id, brawlhalla_season)
        end = min(season.ends_at, now)
        detail.legend = legend_of_season(
            [
                await self._legends.list_between(player.id, season.starts_at, end)
                for player in await self._network.tracked_players(guild_id)
            ]
        )
        detail.tournaments = [
            t
            for t in await self._tournaments.list_for_guild(guild_id, limit=200)
            if season.starts_at <= _aware(t.started_at or t.created_at) < season.ends_at
        ]
        return detail

    async def _top(self, guild_id: int, brawlhalla_season: int) -> list[RankingRow]:
        board = await self._rankings.pakistan(guild_id, season=brawlhalla_season)
        return ranked_rows(board, "1v1")[:TOP_SIZE]

    async def _rising(self, guild_id: int, brawlhalla_season: int) -> SeasonRiser | None:
        """Biggest first-to-last rating gain within the season, board players."""
        best: SeasonRiser | None = None
        for _entry, player in await self._board.list_active(guild_id):
            ratings = [
                s.rating
                for s in await self._ranking.list_for_season(player.id, brawlhalla_season)
                if s.rating is not None
            ]
            if len(ratings) < 2 or ratings[-1] <= ratings[0]:
                continue
            gain = ratings[-1] - ratings[0]
            if best is None or gain > best.rating_gain:
                best = SeasonRiser(player=player, rating_gain=gain, rating=ratings[-1])
        return best
