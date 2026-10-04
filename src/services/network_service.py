"""Network-wide public views for BRAWLISTAN (docs/DECISIONS.md ADR-104).

The site's subject is every tracked player, not only the clan: anyone on the
Pakistan board plus every linked member. This collects that set once, so
network views count each player exactly once. Discord-free, like every service
the API uses.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from services.clan_service import LegendMetaEntry, aggregate_legend_meta


class NetworkService:
    def __init__(self, session: AsyncSession) -> None:
        self._board = PakistanBoardRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._legends = LegendSnapshotRepository(session)

    async def tracked_players(self, guild_id: int) -> list[BrawlhallaPlayer]:
        """Pakistan-board players plus linked members, each once."""
        players: dict[int, BrawlhallaPlayer] = {}
        for _entry, player in await self._board.list_active(guild_id):
            players[player.id] = player
        for _member, player, _discord_id in await self._links.list_active_for_guild(guild_id):
            players.setdefault(player.id, player)
        return list(players.values())

    async def legend_meta(self, guild_id: int, *, limit: int = 10) -> list[LegendMetaEntry]:
        """Most-played Legends across the network, from each player's latest
        per-Legend snapshot (lifetime games from the stats endpoint).
        """
        return aggregate_legend_meta(
            [
                await self._legends.list_latest_per_legend(player.id)
                for player in await self.tracked_players(guild_id)
            ],
            limit=limit,
        )
