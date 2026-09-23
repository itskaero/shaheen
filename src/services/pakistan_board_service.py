"""The Pakistan leaderboard (docs/DECISIONS.md ADR-099) — usable without Discord.

The clan board is whoever /link'd; this one is Pakistan's scene: members add
themselves, and staff can add any Pakistani player by Brawlhalla ID, Discord
member or not. Nothing is inferred — the Brawlhalla API reports a server
region ("SEA"), never a country — so every entry is an explicit opt-in.

Resolving an identifier to a player stays with LinkService.resolve_candidate
(same path /link uses); these methods take the already-confirmed candidate.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ShaheenError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from integrations.brawlhalla.models import SearchResult

# Every entry costs two Brawlhalla API calls per snapshot tick, on top of the
# clan's own; the cap keeps a staff bulk-add from eating the API quota.
MAX_PAKISTAN_BOARD = 150


@dataclass
class PakistanJoinOutcome:
    player: BrawlhallaPlayer
    replaced_player_name: str | None


@dataclass
class PakistanBoardRow:
    player: BrawlhallaPlayer
    snapshot: RankingSnapshot
    is_clan_member: bool


class PakistanBoardService:
    def __init__(self, session: AsyncSession) -> None:
        self._board = PakistanBoardRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)

    async def _player_for(self, candidate: SearchResult) -> BrawlhallaPlayer:
        existing = await self._players.get_by_brawlhalla_id(candidate.brawlhalla_id)
        if existing is not None:
            existing.player_name = candidate.name
            return existing
        # Region is filled by the first snapshot; upsert(region=None) on an
        # existing row would wipe the one /link stored, hence the branch above.
        return await self._players.upsert(
            brawlhalla_player_id=candidate.brawlhalla_id, player_name=candidate.name, region=None
        )

    async def _ensure_room(self, guild_id: int) -> None:
        if await self._board.count_active(guild_id) >= MAX_PAKISTAN_BOARD:
            raise ShaheenError(
                f"The Pakistan leaderboard is full ({MAX_PAKISTAN_BOARD} players) — "
                "ask staff to remove inactive entries first."
            )

    async def join(
        self, *, guild_id: int, discord_id: int, candidate: SearchResult
    ) -> PakistanJoinOutcome:
        """Add the caller's own Brawlhalla account. One self-entry per member:
        joining with a different account replaces the previous one.
        """
        player = await self._player_for(candidate)
        on_board = await self._board.get_active(guild_id, player.id)
        if on_board is not None:
            if on_board.owner_discord_id == discord_id:
                raise ShaheenError(f"{player.player_name} is already on the Pakistan leaderboard.")
            if on_board.owner_discord_id is not None:
                raise ShaheenError(
                    f"{player.player_name} is already on the Pakistan leaderboard under "
                    "another member."
                )
            # Staff added this player before they joined — they claim it.
            previous = await self._board.get_active_for_owner(guild_id, discord_id)
            if previous is not None:
                await self._board.remove(previous)
            on_board.owner_discord_id = discord_id
            return PakistanJoinOutcome(player=player, replaced_player_name=None)

        replaced_name = None
        previous = await self._board.get_active_for_owner(guild_id, discord_id)
        if previous is not None:
            old_player = await self._players.get_by_id(previous.brawlhalla_player_id)
            replaced_name = old_player.player_name if old_player else None
            await self._board.remove(previous)
        else:
            await self._ensure_room(guild_id)

        await self._board.add(
            guild_id=guild_id,
            player_id=player.id,
            added_by_discord_id=discord_id,
            owner_discord_id=discord_id,
        )
        return PakistanJoinOutcome(player=player, replaced_player_name=replaced_name)

    async def add(
        self, *, guild_id: int, added_by_discord_id: int, candidate: SearchResult
    ) -> BrawlhallaPlayer:
        """Staff add — any player, no Discord member required."""
        player = await self._player_for(candidate)
        if await self._board.get_active(guild_id, player.id) is not None:
            raise ShaheenError(f"{player.player_name} is already on the Pakistan leaderboard.")
        await self._ensure_room(guild_id)
        await self._board.add(
            guild_id=guild_id,
            player_id=player.id,
            added_by_discord_id=added_by_discord_id,
            owner_discord_id=None,
        )
        return player

    async def leave(self, *, guild_id: int, discord_id: int) -> BrawlhallaPlayer | None:
        entry = await self._board.get_active_for_owner(guild_id, discord_id)
        if entry is None:
            return None
        await self._board.remove(entry)
        return await self._players.get_by_id(entry.brawlhalla_player_id)

    async def remove(self, *, guild_id: int, brawlhalla_id: int) -> BrawlhallaPlayer | None:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_id)
        if player is None:
            return None
        entry = await self._board.get_active(guild_id, player.id)
        if entry is None:
            return None
        await self._board.remove(entry)
        return player

    async def current_season(self) -> int | None:
        return await self._ranking.current_season()

    async def leaderboard(self, guild_id: int, *, limit: int = 10) -> list[PakistanBoardRow]:
        """Current-season only, like the clan board (docs/DECISIONS.md ADR-088)."""
        season = await self._ranking.current_season()
        clan_player_ids = {
            player.id for _m, player, _d in await self._links.list_active_for_guild(guild_id)
        }
        rows: list[PakistanBoardRow] = []
        for _entry, player in await self._board.list_active(guild_id):
            latest = await self._ranking.get_latest(player.id, season=season)
            if latest is not None:
                rows.append(
                    PakistanBoardRow(
                        player=player, snapshot=latest, is_clan_member=player.id in clan_player_ids
                    )
                )
        rows.sort(key=lambda row: row.snapshot.rating or -1, reverse=True)
        return rows[:limit]
