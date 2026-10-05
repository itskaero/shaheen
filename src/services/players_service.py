"""The players directory and per-player season history (docs/DECISIONS.md ADR-106).

Discord-free and Brawlhalla-identity-only (ADR-040). The directory covers
every tracked player: everyone on the Pakistan board plus every linked
member, each once (services/network_service.py).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.team_repository import TeamRepository
from services.rankings_service import PAKISTAN, shown_tag
from services.seasons import pakistan_season

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def player_slug(player_name: str, brawlhalla_id: int) -> str:
    """URL slug for a player, e.g. ("Khan Bhai!", 123) -> "khan-bhai-123".

    The id suffix makes it unique and is what the site actually resolves; the
    name part is for people and search engines, and survives renames as a
    harmless stale label.
    """
    ascii_name = (
        unicodedata.normalize("NFKD", player_name).encode("ascii", "ignore").decode("ascii")
    )
    base = _NON_SLUG.sub("-", ascii_name.lower()).strip("-")[:40].strip("-")
    return f"{base}-{brawlhalla_id}" if base else str(brawlhalla_id)


def brawlhalla_id_from_slug(slug: str) -> int | None:
    tail = slug.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


@dataclass
class DirectoryEntry:
    player: BrawlhallaPlayer
    slug: str
    snapshot: RankingSnapshot | None
    country: str | None
    team: str | None
    team_slug: str | None
    team_tag: str | None
    is_claimed: bool
    is_verified: bool
    on_pakistan_board: bool
    main_legend: str | None


@dataclass
class SeasonSummary:
    season: int
    pakistan_season_number: int | None
    pakistan_season_name: str | None
    final_rating: int | None
    peak_rating: int | None
    readings: int


class PlayersService:
    def __init__(self, session: AsyncSession) -> None:
        self._board = PakistanBoardRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._legends = LegendSnapshotRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._teams = TeamRepository(session)

    async def directory(self, guild_id: int) -> list[DirectoryEntry]:
        """Every tracked player, best current-season rating first, then by name."""
        season = await self._ranking.current_season()
        board = {
            player.id: (entry, player) for entry, player in await self._board.list_active(guild_id)
        }
        linked = {
            player.id: player
            for _m, player, _d in await self._links.list_active_for_guild(guild_id)
        }
        players = {**{pid: p for pid, (_e, p) in board.items()}, **linked}
        # Team rosters, clan-synced ones included (ADR-120).
        for pid in await self._teams.active_player_ids(guild_id) - players.keys():
            rostered = await self._players.get_by_id(pid)
            if rostered is not None:
                players[pid] = rostered
        verified = await self._links.verified_player_ids()
        teams = await self._teams.memberships_of(guild_id, list(players))

        entries: list[DirectoryEntry] = []
        for pid, player in players.items():
            board_entry = board.get(pid)
            snapshot = (
                await self._ranking.get_latest(pid, season=season) if season is not None else None
            )
            legends = await self._legends.list_latest_per_legend(pid)
            main = max(legends, key=lambda legend: legend.games, default=None)
            entries.append(
                DirectoryEntry(
                    player=player,
                    slug=player_slug(player.player_name, player.brawlhalla_player_id),
                    snapshot=snapshot,
                    country=PAKISTAN if board_entry else None,
                    team=teams[pid][0].name if pid in teams else None,
                    team_slug=teams[pid][0].slug if pid in teams else None,
                    team_tag=shown_tag(teams.get(pid)),
                    # Claimed = tied to a Discord member, either by /pakistan
                    # join or by /link (ADR-100).
                    is_claimed=pid in linked
                    or (board_entry is not None and board_entry[0].owner_discord_id is not None),
                    is_verified=pid in verified,
                    on_pakistan_board=board_entry is not None,
                    main_legend=main.legend_name_key if main and main.games > 0 else None,
                )
            )
        entries.sort(
            key=lambda e: (
                -(e.snapshot.rating if e.snapshot and e.snapshot.rating else 0),
                e.player.player_name.lower(),
            )
        )
        return entries

    async def season_history(self, brawlhalla_id: int) -> list[SeasonSummary] | None:
        """None when the player isn't known at all."""
        player = await self._players.get_by_brawlhalla_id(brawlhalla_id)
        if player is None:
            return None
        summaries: list[SeasonSummary] = []
        for season, final, peak, readings in await self._ranking.season_summaries(player.id):
            named = pakistan_season(season)
            summaries.append(
                SeasonSummary(
                    season=season,
                    pakistan_season_number=named.number if named else None,
                    pakistan_season_name=named.name if named else None,
                    final_rating=final,
                    peak_rating=peak,
                    readings=readings,
                )
            )
        return summaries
