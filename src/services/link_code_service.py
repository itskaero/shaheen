"""One-time codes that link a Discord account to a website profile
(docs/DECISIONS.md ADR-107).

Flow: `/link` (no arguments) issues a code to the Discord member; on the
website they open their player profile, choose "Claim this profile" and
enter it. The claim links that Discord account to that Brawlhalla player
through LinkService.attach, the same rules /link uses (no takeovers).

What a claim proves: that whoever typed the code controls the Discord
account. It cannot prove they own the Brawlhalla account, which is why
"Verified" is a separate, staff-only step (/verify).

Codes: 8 characters from an unambiguous alphabet (no 0/O, 1/I/L), shown as
XXXX-XXXX, stored only as a SHA-256 hash, single use, 15 minutes, and a new
code replaces any pending one. Issuing is capped per member per hour.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import InvalidCodeError, NotFoundError, RateLimitedError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.link_code import LinkCode
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.link_code_repository import LinkCodeRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from integrations.brawlhalla.service import BrawlhallaService
from services.link_service import LinkService

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
CODE_TTL = timedelta(minutes=15)
MAX_CODES_PER_HOUR = 5
_INVALID = "That code is invalid or has expired. Run /link in the Discord for a new one."


def normalize_code(raw: str) -> str | None:
    """Normalize user input to a bare code (e.g. "abcd-efgh " -> "ABCDEFGH").

    Returns None if it can't be a code at all.
    """
    code = "".join(ch for ch in raw.upper() if ch.isalnum())
    if len(code) != CODE_LENGTH or any(ch not in CODE_ALPHABET for ch in code):
        return None
    return code


def format_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def _aware(moment: datetime) -> datetime:
    # SQLite hands timestamps back naive; Postgres keeps the zone.
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


@dataclass
class IssuedCode:
    code: str  # display form, XXXX-XXXX
    expires_at: datetime


@dataclass
class ClaimOutcome:
    player: BrawlhallaPlayer
    discord_id: int


class LinkCodeService:
    def __init__(self, session: AsyncSession, brawlhalla: BrawlhallaService | None = None) -> None:
        self._codes = LinkCodeRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._discord_users = DiscordUserRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._audit = AuditLogRepository(session)
        # LinkService only needs Brawlhalla for /link's lookups; attach() doesn't.
        self._links = LinkService(session, brawlhalla)  # type: ignore[arg-type]

    async def issue(
        self, *, guild_id: int, discord_id: int, now: datetime | None = None
    ) -> IssuedCode:
        now = now or datetime.now(UTC)
        recent = await self._codes.count_issued_since(
            guild_id=guild_id, discord_id=discord_id, since=now - timedelta(hours=1)
        )
        if recent >= MAX_CODES_PER_HOUR:
            raise RateLimitedError("You've asked for a lot of codes. Try again in an hour.")
        await self._codes.expire_pending(guild_id=guild_id, discord_id=discord_id, now=now)
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        expires_at = now + CODE_TTL
        await self._codes.add(
            LinkCode(
                code_hash=hash_code(code),
                guild_id=guild_id,
                discord_id=discord_id,
                expires_at=expires_at,
            )
        )
        return IssuedCode(code=format_code(code), expires_at=expires_at)

    async def claim(
        self,
        *,
        guild_id: int,
        raw_code: str,
        brawlhalla_id: int,
        now: datetime | None = None,
    ) -> ClaimOutcome:
        now = now or datetime.now(UTC)
        code = normalize_code(raw_code)
        row = await self._codes.get_by_hash(hash_code(code)) if code else None
        if (
            row is None
            or row.guild_id != guild_id
            or row.used_at is not None
            or _aware(row.expires_at) <= now
        ):
            raise InvalidCodeError(_INVALID)

        player = await self._players.get_by_brawlhalla_id(brawlhalla_id)
        if player is None:
            raise NotFoundError("BRAWLISTAN doesn't track that player yet.")

        discord_user = await self._discord_users.get_or_create(row.discord_id)
        member = await self._members.get_or_create(
            discord_user_id=discord_user.id, guild_id=guild_id
        )
        await self._links.attach(
            guild_id=guild_id, discord_id=row.discord_id, member=member, player=player
        )
        row.used_at = now
        row.used_for_player_id = player.id
        await self._audit.add(
            guild_id=guild_id,
            action="link.claim",
            source="website",
            actor_discord_id=row.discord_id,
            subject=f"{player.player_name} ({player.brawlhalla_player_id})",
        )
        return ClaimOutcome(player=player, discord_id=row.discord_id)
