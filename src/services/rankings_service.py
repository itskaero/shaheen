"""The Rankings page's data (docs/DECISIONS.md ADR-105).

One payload backs every bracket tab (Pakistan, Global, 1v1, 2v2): each row
carries the player's current-season 1v1 and best-2v2 standing, their 7-day
rating trend, their most-played Legend and their team. The page sorts and
filters it client-side, so the site never calls the Brawlhalla API and the
whole board can be cached as one snapshot file.

Discord-free and Brawlhalla-identity-only (ADR-040): claim status and clan
membership are booleans/labels, never Discord ids.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository

TREND_WINDOW = timedelta(days=7)
# Every Pakistan-board player is on the board because they (or staff) put
# them on the Pakistan board, so that is the country it can honestly state.
PAKISTAN = "PK"
FOUNDING_TEAM = "SHAHEEN"


@dataclass
class RankingRow:
    player: BrawlhallaPlayer
    snapshot: RankingSnapshot
    is_claimed: bool
    team: str | None
    country: str
    # Rating change over TREND_WINDOW within the season; None when there's
    # nothing to compare against yet.
    trend: int | None
    main_legend: str | None


@dataclass
class RankingsBoard:
    season: int | None
    seasons: list[int] = field(default_factory=list)
    rows: list[RankingRow] = field(default_factory=list)


class RankingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._board = PakistanBoardRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._legends = LegendSnapshotRepository(session)

    async def pakistan(
        self, guild_id: int, *, season: int | None = None, now: datetime | None = None
    ) -> RankingsBoard:
        """Every Pakistan-board player with a reading in `season` (default: current).

        Unplaced players are included; each tab keeps only the rows that have
        the number it ranks by.
        """
        seasons = await self._ranking.list_seasons()
        season = season if season is not None else (seasons[0] if seasons else None)
        board = RankingsBoard(season=season, seasons=seasons)
        if season is None:
            return board

        now = now or datetime.now(UTC)
        clan_player_ids = {
            player.id for _m, player, _d in await self._links.list_active_for_guild(guild_id)
        }
        for entry, player in await self._board.list_active(guild_id):
            latest = await self._ranking.get_latest(player.id, season=season)
            if latest is None:
                continue
            board.rows.append(
                RankingRow(
                    player=player,
                    snapshot=latest,
                    is_claimed=entry.owner_discord_id is not None,
                    team=FOUNDING_TEAM if player.id in clan_player_ids else None,
                    country=PAKISTAN,
                    trend=await self._trend(player.id, season, now),
                    main_legend=await self._main_legend(player.id),
                )
            )
        board.rows.sort(key=lambda row: row.snapshot.rating or 0, reverse=True)
        return board

    async def _trend(self, player_id: int, season: int, now: datetime) -> int | None:
        ratings = [
            s.rating
            for s in await self._ranking.list_since(player_id, now - TREND_WINDOW)
            if s.season == season and s.rating is not None
        ]
        return ratings[-1] - ratings[0] if len(ratings) >= 2 else None

    async def _main_legend(self, player_id: int) -> str | None:
        """Most-played Legend by lifetime games (the stats endpoint)."""
        legends = await self._legends.list_latest_per_legend(player_id)
        best = max(legends, key=lambda legend: legend.games, default=None)
        return best.legend_name_key if best and best.games > 0 else None
