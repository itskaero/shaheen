"""Read-only Brawlhalla lookup for players who haven't linked (ADR-083).

Brawlhalla's API has no name search — only `/search?steamid=` and
`/player/{id}/...` — so this takes a Steam64 or Brawlhalla ID the same way
/link does, and reuses LinkService.resolve_candidate for it rather than
re-implementing the resolution + error translation.

Nothing is written: no DiscordUser, no ShaheenMember, no link, no snapshot.
The clan-relevant half is ClanService.rank_context — a bare rating means
little on its own, so every lookup is reported next to where it would sit
on Shaheen's own ladder.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from integrations.brawlhalla.models import PlayerRankedResponse, PlayerStatsResponse
from integrations.brawlhalla.service import BrawlhallaService
from services.clan_service import ClanRankContext, ClanService
from services.link_service import LinkService
from services.profile_service import ProfileService


@dataclass
class LookupResult:
    player_name: str
    brawlhalla_id: int
    stats: PlayerStatsResponse
    ranked: PlayerRankedResponse | None
    # None when the player has no ranked rating to place — an unranked
    # player can't be slotted into a ladder.
    clan_context: ClanRankContext | None


class LookupService:
    def __init__(self, session: AsyncSession, brawlhalla: BrawlhallaService) -> None:
        self._links = LinkService(session, brawlhalla)
        self._profiles = ProfileService(session, self._links, brawlhalla)
        self._clan = ClanService(session)

    async def lookup(self, *, guild_id: int, identifier: str) -> LookupResult:
        """Raises NotFoundError for an unknown ID, IntegrationError if the
        Brawlhalla API is unavailable (both from LinkService/ProfileService).
        """
        candidate = await self._links.resolve_candidate(identifier)
        stats = await self._profiles.get_stats(candidate.brawlhalla_id)
        ranked = await self._profiles.get_ranked(candidate.brawlhalla_id)

        clan_context = None
        if ranked is not None and ranked.rating is not None:
            clan_context = await self._clan.rank_context(guild_id, ranked.rating)

        return LookupResult(
            player_name=candidate.name,
            brawlhalla_id=candidate.brawlhalla_id,
            stats=stats,
            ranked=ranked,
            clan_context=clan_context,
        )
