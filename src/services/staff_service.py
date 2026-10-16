"""Founders and Admins for the Founding Team page (docs/DECISIONS.md ADR-135).

The bot passes in who holds the Founder and Admin roles (`StaffHolder`); this
service mirrors them into `staff_members` and builds the public directory.
Discord-free, like coaching_service.py.

What the public directory shows, by the owner's decision (ADR-135 amends
ADR-040 for these two roles only): a name, the role and the avatar image.
The name is the member's linked Brawlhalla name when they have linked,
otherwise their server display name. Never a Discord id, username or CDN
URL: the avatar is served as image bytes the bot downloaded.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.staff_member import STAFF_ROLES, StaffMember
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.staff_repository import StaffRepository
from services.players_service import player_slug

# A 128 px avatar is ~5-20 KB; anything far bigger isn't an avatar.
MAX_AVATAR_BYTES = 256 * 1024


def image_type(data: bytes) -> str | None:
    """The image's MIME type from its magic bytes, for the formats Discord serves."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


@dataclass(frozen=True)
class StaffHolder:
    discord_id: int
    display_name: str
    role: str  # "founder" or "admin": the highest one held
    position: int = 0  # order within the role, as in the server's member list
    avatar_key: str | None = None  # Discord's avatar hash


@dataclass(frozen=True)
class StaffSyncResult:
    added: int = 0
    updated: int = 0
    deactivated: int = 0
    # Members whose avatar is missing or changed: the bot downloads these.
    avatars_needed: tuple[int, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.added or self.updated or self.deactivated)


@dataclass(frozen=True)
class StaffEntry:
    name: str
    role: str
    avatar_data_uri: str | None
    player_slug: str | None  # their player page, when linked


class StaffService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = StaffRepository(session)
        self._links = MemberPlayerLinkRepository(session)

    async def sync(self, guild_id: int, holders: Sequence[StaffHolder]) -> StaffSyncResult:
        """Mirror the role holders (idempotent; writes only diffs)."""
        held = {h.discord_id: h for h in holders if h.role in STAFF_ROLES}
        linked = {
            discord_id: player.id
            for _member, player, discord_id in await self._links.list_active_for_guild(guild_id)
        }
        added = updated = deactivated = 0
        needed: list[int] = []
        known = {s.discord_id: s for s in await self._repo.all_for_guild(guild_id)}
        for discord_id, row in known.items():
            holder = held.get(discord_id)
            if holder is None:
                if row.active:
                    row.active = False
                    deactivated += 1
                continue
            before = (
                row.active,
                row.role,
                row.display_name,
                row.position,
                row.brawlhalla_player_id,
            )
            row.active = True
            row.role = holder.role
            row.display_name = holder.display_name[:64]
            row.position = holder.position
            row.brawlhalla_player_id = linked.get(discord_id)
            if before != (
                row.active,
                row.role,
                row.display_name,
                row.position,
                row.brawlhalla_player_id,
            ):
                updated += 1
            if holder.avatar_key != row.avatar_key or (holder.avatar_key and row.avatar is None):
                if holder.avatar_key is None:  # back to Discord's default avatar
                    row.avatar_key = row.avatar = row.avatar_type = None
                    updated += 1
                else:
                    needed.append(discord_id)
        for discord_id, holder in held.items():
            if discord_id in known:
                continue
            await self._repo.add(
                StaffMember(
                    guild_id=guild_id,
                    discord_id=discord_id,
                    role=holder.role,
                    display_name=holder.display_name[:64],
                    position=holder.position,
                    brawlhalla_player_id=linked.get(discord_id),
                    active=True,
                )
            )
            added += 1
            if holder.avatar_key:
                needed.append(discord_id)
        return StaffSyncResult(added, updated, deactivated, tuple(needed))

    async def set_avatar(self, guild_id: int, discord_id: int, *, key: str, data: bytes) -> bool:
        """Store a downloaded avatar. Refuses anything that isn't a small image."""
        content_type = image_type(data)
        if content_type is None or len(data) > MAX_AVATAR_BYTES:
            return False
        row = await self._repo.by_discord(guild_id, discord_id)
        if row is None:
            return False
        row.avatar_key, row.avatar, row.avatar_type = key[:64], data, content_type
        return True

    async def directory(self, guild_id: int) -> list[StaffEntry]:
        """Founders first, then Admins, each in the server's order."""
        rows = await self._repo.active_with_players(guild_id)
        rows.sort(
            key=lambda r: (STAFF_ROLES.index(r[0].role), r[0].position, r[0].display_name.lower())
        )
        return [
            StaffEntry(
                name=player.player_name if player is not None else staff.display_name,
                role=staff.role,
                avatar_data_uri=(
                    f"data:{staff.avatar_type};base64,{base64.b64encode(staff.avatar).decode()}"
                    if staff.avatar and staff.avatar_type
                    else None
                ),
                player_slug=(
                    player_slug(player.player_name, player.brawlhalla_player_id)
                    if player is not None
                    else None
                ),
            )
            for staff, player in rows
        ]
