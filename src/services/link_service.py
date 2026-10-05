"""Business logic behind /link and /unlink — usable without Discord.

Orchestrates DiscordUser/ShaheenMember/BrawlhallaPlayer/MemberPlayerLink
persistence and the Brawlhalla lookup, translating integration failures
into core.exceptions so cogs never see raw external errors
(docs/COMMANDS.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, IntegrationError, NotFoundError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.shaheen_member import ShaheenMember
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from integrations.brawlhalla.errors import BrawlhallaAPIError, BrawlhallaNotFound
from integrations.brawlhalla.models import SearchResult
from integrations.brawlhalla.service import BrawlhallaService
from services.achievement_service import AchievementService
from services.achievements import FIRST_LINK
from services.pakistan_board_service import PakistanBoardService


@dataclass
class LinkOutcome:
    member: ShaheenMember
    player: BrawlhallaPlayer
    previous_player_name: str | None
    first_link_awarded: bool = False
    # Linking puts you on the Pakistan rankings unless you opted out (ADR-125).
    on_pakistan_board: bool = False


class LinkService:
    def __init__(self, session: AsyncSession, brawlhalla: BrawlhallaService) -> None:
        self._session = session
        self._brawlhalla = brawlhalla
        self._discord_users = DiscordUserRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._board = PakistanBoardRepository(session)
        self._pakistan = PakistanBoardService(session)
        self._achievement_service = AchievementService(session)

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
        first_link_awarded = await self.attach(
            guild_id=guild_id, discord_id=discord_id, member=member, player=player
        )

        return LinkOutcome(
            member=member,
            player=player,
            previous_player_name=previous_player_name,
            first_link_awarded=first_link_awarded,
            on_pakistan_board=await self._pakistan.is_on_board(
                guild_id=guild_id, player_id=player.id
            ),
        )

    async def attach(
        self,
        *,
        guild_id: int,
        discord_id: int,
        member: ShaheenMember,
        player: BrawlhallaPlayer,
    ) -> bool:
        """Make `player` the member's active link — the one place both /link
        and the website claim (ADR-107) go through.

        Refuses an account another member already holds, or a Pakistan-board
        entry claimed by someone else: linking is never a takeover. Returns
        whether the first-link achievement was awarded.
        """
        holder = await self._links.get_active_by_player(player.id)
        if holder is not None and holder.shaheen_member_id != member.id:
            raise ConflictError(
                f"**{player.player_name}** is already linked to another member. "
                "If it's yours, ask staff to sort it out."
            )
        board_entry = await self._board.get_active(guild_id, player.id)
        if board_entry is not None and board_entry.owner_discord_id not in (None, discord_id):
            raise ConflictError(
                f"**{player.player_name}** is already claimed on the Pakistan board by "
                "another member. If it's yours, ask staff."
            )
        if holder is None:
            await self._links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
        # Linking claims the board spot, or puts you on the board (ADR-125).
        await self._pakistan.on_link(guild_id=guild_id, discord_id=discord_id, player=player)
        return await self._award_first_link(member, player)

    async def set_verified(
        self, *, guild_id: int, discord_id: int, staff_discord_id: int, verified: bool
    ) -> BrawlhallaPlayer | None:
        """Staff confirm (or withdraw) that a member owns their linked account
        (/verify, ADR-107). Returns the linked player, or None if not linked.
        """
        active = await self.get_active_link(guild_id=guild_id, discord_id=discord_id)
        if active is None:
            return None
        member, player = active
        link = await self._links.get_active(member.id)
        assert link is not None  # get_active_link just found it
        link.verified_at = datetime.now(UTC) if verified else None
        link.verified_by_discord_id = staff_discord_id if verified else None
        return player

    async def _award_first_link(self, member: ShaheenMember, player: BrawlhallaPlayer) -> bool:
        awarded = await self._achievement_service.award(
            shaheen_member_id=member.id,
            definition=FIRST_LINK,
            extra={"player_name": player.player_name},
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
