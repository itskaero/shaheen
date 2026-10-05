"""The Pakistan leaderboard (docs/DECISIONS.md ADR-099) — usable without Discord.

The clan board is whoever /link'd; this one is Pakistan's scene. A player is
on it when (ADR-125):
- they linked (/link puts you on it) or joined themselves (/pakistan join);
- staff added them (/pakistan add), Discord member or not;
- they're on a Pakistani team's roster (the team sync, every snapshot tick).

The Brawlhalla API reports a server region ("SEA"), never a country, so
nothing is inferred beyond that. Leaving (/pakistan leave) or a staff removal
is remembered, so neither /link nor the team sync puts that player back.

Resolving an identifier to a player stays with LinkService.resolve_candidate
(same path /link uses); these methods take the already-confirmed candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ShaheenError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.pakistan_board_entry import SOURCE_SELF, SOURCE_STAFF, SOURCE_TEAM
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.team_repository import TeamRepository
from integrations.brawlhalla.models import SearchResult

# Every entry costs two Brawlhalla API calls per snapshot tick, on top of the
# clan's own; the cap keeps a staff bulk-add from eating the API quota.
# Team-roster and linked entries don't add calls (they're snapshotted anyway),
# so team entries don't count towards it and /link never hits it.
MAX_PAKISTAN_BOARD = 150

# Teams whose rosters count as Pakistani players (teams.country, ADR-125).
PAKISTAN_TEAM_COUNTRY = "PK"

# added_by_discord_id for entries the bot made itself (the team sync).
SYSTEM_DISCORD_ID = 0


@dataclass(frozen=True)
class TeamBoardSync:
    added: int = 0
    removed: int = 0


@dataclass
class PakistanJoinOutcome:
    player: BrawlhallaPlayer
    replaced_player_name: str | None


@dataclass
class PakistanBoardRow:
    player: BrawlhallaPlayer
    snapshot: RankingSnapshot
    is_clan_member: bool
    # The Discord member who claimed this entry via /pakistan join; None
    # while it's a staff-added, unclaimed spot (docs/DECISIONS.md ADR-100).
    owner_discord_id: int | None = None

    @property
    def is_claimed(self) -> bool:
        return self.owner_discord_id is not None


@dataclass
class PakistanClimber:
    player: BrawlhallaPlayer
    rating_gain: int
    owner_discord_id: int | None
    # The latest rating inside the window — where the climb ended.
    rating: int = 0

    @property
    def is_claimed(self) -> bool:
        return self.owner_discord_id is not None


class PakistanBoardService:
    def __init__(self, session: AsyncSession) -> None:
        self._board = PakistanBoardRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._teams = TeamRepository(session)

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
        return await self._join_player(guild_id, discord_id, player)

    async def join_linked(self, *, guild_id: int, discord_id: int) -> PakistanJoinOutcome:
        """/pakistan join with no ID: the member's linked account (ADR-125)."""
        player = await self._linked_player(guild_id, discord_id)
        if player is None:
            raise ShaheenError(
                "You haven't linked a Brawlhalla account. Run `/link` (it puts you on the "
                "Pakistan rankings), or `/pakistan join` with your Brawlhalla ID."
            )
        return await self._join_player(guild_id, discord_id, player)

    async def _join_player(
        self, guild_id: int, discord_id: int, player: BrawlhallaPlayer
    ) -> PakistanJoinOutcome:
        on_board = await self._board.get_active(guild_id, player.id)
        if on_board is not None:
            if on_board.owner_discord_id == discord_id:
                raise ShaheenError(f"{player.player_name} is already on the Pakistan leaderboard.")
            if on_board.owner_discord_id is not None:
                raise ShaheenError(
                    f"{player.player_name} is already on the Pakistan leaderboard under "
                    "another member."
                )
            # Staff or a team roster put this player on before they joined: they claim it.
            previous = await self._board.get_active_for_owner(guild_id, discord_id)
            if previous is not None:
                await self._board.remove(previous, excluded=True)
            on_board.owner_discord_id = discord_id
            return PakistanJoinOutcome(player=player, replaced_player_name=None)

        replaced_name = None
        previous = await self._board.get_active_for_owner(guild_id, discord_id)
        if previous is not None:
            old_player = await self._players.get_by_id(previous.brawlhalla_player_id)
            replaced_name = old_player.player_name if old_player else None
            await self._board.remove(previous, excluded=True)
        elif not await self._is_linked_to(guild_id, discord_id, player):
            await self._ensure_room(guild_id)

        await self._board.add(
            guild_id=guild_id,
            player_id=player.id,
            added_by_discord_id=discord_id,
            owner_discord_id=discord_id,
            source=SOURCE_SELF,
        )
        return PakistanJoinOutcome(player=player, replaced_player_name=replaced_name)

    async def on_link(self, *, guild_id: int, discord_id: int, player: BrawlhallaPlayer) -> bool:
        """/link (and the website claim) put the member on the board
        (ADR-125), unless that player opted out or was removed by staff.
        Claims an unowned spot, and replaces the member's own entry for a
        different account. Returns whether the player is on the board."""
        on_board = await self._board.get_active(guild_id, player.id)
        if on_board is not None:
            if on_board.owner_discord_id is None:
                on_board.owner_discord_id = discord_id
            return True
        if player.id in await self._board.excluded_player_ids(guild_id):
            return False
        previous = await self._board.get_active_for_owner(guild_id, discord_id)
        if previous is not None:
            await self._board.remove(previous, excluded=True)
        await self._board.add(
            guild_id=guild_id,
            player_id=player.id,
            added_by_discord_id=discord_id,
            owner_discord_id=discord_id,
            source=SOURCE_SELF,
        )
        return True

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
            source=SOURCE_STAFF,
        )
        return player

    async def leave(self, *, guild_id: int, discord_id: int) -> BrawlhallaPlayer | None:
        """Take the member off: the entry they own, or their linked account's
        (say a team roster put it there). Remembered as an opt-out."""
        entry = await self._board.get_active_for_owner(guild_id, discord_id)
        if entry is None:
            linked = await self._linked_player(guild_id, discord_id)
            if linked is not None:
                entry = await self._board.get_active(guild_id, linked.id)
        if entry is None:
            return None
        await self._board.remove(entry, excluded=True)
        return await self._players.get_by_id(entry.brawlhalla_player_id)

    async def remove(self, *, guild_id: int, brawlhalla_id: int) -> BrawlhallaPlayer | None:
        """Staff removal; the team sync won't add the player back."""
        player = await self._players.get_by_brawlhalla_id(brawlhalla_id)
        if player is None:
            return None
        entry = await self._board.get_active(guild_id, player.id)
        if entry is None:
            return None
        await self._board.remove(entry, excluded=True)
        return player

    async def is_on_board(self, *, guild_id: int, player_id: int) -> bool:
        return await self._board.get_active(guild_id, player_id) is not None

    async def sync_team_rosters(self, guild_id: int) -> TeamBoardSync:
        """Everyone on a Pakistani team's roster is on the board (ADR-125).

        Adds rostered players who aren't on it and haven't opted out; takes
        off the entries this sync added (unclaimed ones) once the player is
        no longer on any Pakistani team. Entries from /link, /pakistan join
        or staff are never touched.
        """
        rostered = await self._teams.active_player_ids(guild_id, country=PAKISTAN_TEAM_COUNTRY)
        active = await self._board.list_active(guild_id)
        on_board = {player.id for _entry, player in active}
        excluded = await self._board.excluded_player_ids(guild_id)

        added = 0
        for player_id in sorted(rostered - on_board - excluded):
            await self._board.add(
                guild_id=guild_id,
                player_id=player_id,
                added_by_discord_id=SYSTEM_DISCORD_ID,
                owner_discord_id=None,
                source=SOURCE_TEAM,
            )
            added += 1

        removed = 0
        for entry, player in active:
            if (
                entry.source == SOURCE_TEAM
                and entry.owner_discord_id is None
                and player.id not in rostered
            ):
                await self._board.remove(entry)
                removed += 1
        return TeamBoardSync(added=added, removed=removed)

    async def _linked_player(self, guild_id: int, discord_id: int) -> BrawlhallaPlayer | None:
        for _member, player, linked_discord_id in await self._links.list_active_for_guild(guild_id):
            if linked_discord_id == discord_id:
                return player
        return None

    async def _is_linked_to(self, guild_id: int, discord_id: int, player: BrawlhallaPlayer) -> bool:
        linked = await self._linked_player(guild_id, discord_id)
        return linked is not None and linked.id == player.id

    async def current_season(self) -> int | None:
        return await self._ranking.current_season()

    async def leaderboard(self, guild_id: int, *, limit: int = 10) -> list[PakistanBoardRow]:
        """Current-season only, like the clan board (docs/DECISIONS.md ADR-088)."""
        season = await self._ranking.current_season()
        clan_player_ids = {
            player.id for _m, player, _d in await self._links.list_active_for_guild(guild_id)
        }
        rows: list[PakistanBoardRow] = []
        for entry, player in await self._board.list_active(guild_id):
            latest = await self._ranking.get_latest(player.id, season=season)
            # Placed players only: right after a season reset everyone reads
            # unplaced (ADR-101), and an unrated row must never outrank a
            # rated one into the Top 10 role.
            if latest is not None and latest.rating is not None:
                rows.append(
                    PakistanBoardRow(
                        player=player,
                        snapshot=latest,
                        is_clan_member=player.id in clan_player_ids,
                        owner_discord_id=entry.owner_discord_id,
                    )
                )
        rows.sort(key=lambda row: row.snapshot.rating or 0, reverse=True)
        return rows[:limit]

    async def climbers(
        self, guild_id: int, *, since: datetime, limit: int = 5
    ) -> list[PakistanClimber]:
        """Biggest rating gains on the board since `since` — same first-vs-last
        diff the clan digest uses (services/digest_service.py).
        """
        climbers: list[PakistanClimber] = []
        for entry, player in await self._board.list_active(guild_id):
            ratings = [
                s.rating for s in await self._ranking.list_since(player.id, since) if s.rating
            ]
            if len(ratings) >= 2 and ratings[-1] > ratings[0]:
                climbers.append(
                    PakistanClimber(
                        player=player,
                        rating_gain=ratings[-1] - ratings[0],
                        owner_discord_id=entry.owner_discord_id,
                        rating=ratings[-1],
                    )
                )
        climbers.sort(key=lambda c: c.rating_gain, reverse=True)
        return climbers[:limit]
