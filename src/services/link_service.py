"""Business logic behind /link and /unlink — usable without Discord.

Orchestrates DiscordUser/ShaheenMember/BrawlhallaPlayer/MemberPlayerLink
persistence and the Brawlhalla lookup, translating integration failures
into core.exceptions so cogs never see raw external errors
(docs/COMMANDS.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import IntegrationError, NotFoundError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.shaheen_member import ShaheenMember
from database.repositories.achievement_repository import AchievementRepository
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from integrations.brawlhalla.errors import BrawlhallaAPIError, BrawlhallaNotFound
from integrations.brawlhalla.models import SearchResult
from integrations.brawlhalla.service import BrawlhallaService
from services.achievements import FIRST_LINK


@dataclass
class LinkOutcome:
    member: ShaheenMember
    player: BrawlhallaPlayer
    previous_player_name: str | None
    first_link_awarded: bool = False


class LinkService:
    def __init__(self, session: AsyncSession, brawlhalla: BrawlhallaService) -> None:
        self._session = session
        self._brawlhalla = brawlhalla
        self._discord_users = DiscordUserRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._achievements = AchievementRepository(session)
        self._awards = MemberAchievementRepository(session)

    async def resolve_candidate(self, identifier: str) -> SearchResult:
        """Resolve a user-supplied identifier to a Brawlhalla player.

        Raises NotFoundError if nothing matches, IntegrationError on any
        other Brawlhalla API failure.
        """
        try:
            return await self._brawlhalla.resolve_identifier(identifier)
        except BrawlhallaAPIError as exc:
            raise self._translate(exc, identifier) from exc

    async def get_active_link(
        self, *, guild_id: int, discord_id: int
    ) -> tuple[ShaheenMember, BrawlhallaPlayer] | None:
        discord_user = await self._discord_users.get_by_discord_id(discord_id)
        if discord_user is None:
            return None
        member = await self._members.get(discord_user_id=discord_user.id, guild_id=guild_id)
        if member is None:
            return None
        active = await self._links.get_active(member.id)
        if active is None:
            return None
        player = await self._players.get_by_id(active.brawlhalla_player_id)
        return (member, player) if player is not None else None

    async def link(
        self,
        *,
        guild_id: int,
        discord_id: int,
        joined_at: datetime | None,
        candidate: SearchResult,
    ) -> LinkOutcome:
        discord_user = await self._discord_users.get_or_create(discord_id)
        member = await self._members.get_or_create(
            discord_user_id=discord_user.id, guild_id=guild_id, joined_at=joined_at
        )

        previous_active = await self._links.get_active(member.id)
        previous_player_name = None
        if previous_active is not None:
            previous_player = await self._players.get_by_id(previous_active.brawlhalla_player_id)
            previous_player_name = previous_player.player_name if previous_player else None

        region = None
        try:
            ranked = await self._brawlhalla.get_ranked(candidate.brawlhalla_id)
            region = ranked.region if ranked is not None else None
        except BrawlhallaAPIError:
            pass  # region is a nice-to-have; don't fail the link over it

        player = await self._players.upsert(
            brawlhalla_player_id=candidate.brawlhalla_id,
            player_name=candidate.name,
            region=region,
        )
        await self._links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)

        first_link_awarded = await self._award_first_link(member)

        return LinkOutcome(
            member=member,
            player=player,
            previous_player_name=previous_player_name,
            first_link_awarded=first_link_awarded,
        )

    async def _award_first_link(self, member: ShaheenMember) -> bool:
        catalog_row = await self._achievements.get_by_key(FIRST_LINK.key)
        if catalog_row is None:
            return False  # migrations not run yet; don't block linking over it
        awarded = await self._awards.award(
            shaheen_member_id=member.id, achievement_id=catalog_row.id
        )
        return awarded is not None

    async def unlink(self, *, guild_id: int, discord_id: int) -> BrawlhallaPlayer | None:
        """Returns the player that was unlinked, or None if nothing was linked."""
        active = await self.get_active_link(guild_id=guild_id, discord_id=discord_id)
        if active is None:
            return None
        member, player = active
        await self._links.unlink(member.id)
        return player

    def _translate(self, exc: BrawlhallaAPIError, identifier: str) -> Exception:
        if isinstance(exc, BrawlhallaNotFound):
            return NotFoundError(f"No Brawlhalla player found for {identifier!r}.")
        return IntegrationError("Brawlhalla is not responding right now. Try again shortly.")
