"""Founders and Admins on the Founding Team page (docs/DECISIONS.md ADR-135)."""

from __future__ import annotations

import base64

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from services.staff_service import MAX_AVATAR_BYTES, StaffHolder, StaffService, image_type

GUILD = 1
FOUNDER, ADMIN, OTHER = 100, 200, 300
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 10


async def _link(session: AsyncSession, discord_id: int, brawlhalla_id: int, name: str) -> None:
    user = await DiscordUserRepository(session).get_or_create(discord_id)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD
    )
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=brawlhalla_id, player_name=name, region="sea"
    )
    await MemberPlayerLinkRepository(session).link(
        shaheen_member_id=member.id, brawlhalla_player_id=player.id
    )


def test_image_type_sniffs_magic_bytes() -> None:
    assert image_type(PNG) == "image/png"
    assert image_type(WEBP) == "image/webp"
    assert image_type(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert image_type(b"GIF89a....") == "image/gif"
    assert image_type(b"<svg onload=alert(1)>") is None


async def test_directory_uses_brawlhalla_name_when_linked_and_never_discord_ids(
    session: AsyncSession,
) -> None:
    await _link(session, FOUNDER, 5734378, "kaero.")
    service = StaffService(session)
    result = await service.sync(
        GUILD,
        [
            StaffHolder(ADMIN, "Admin Nick", "admin", position=0, avatar_key="b"),
            StaffHolder(FOUNDER, "Founder Nick", "founder", position=0, avatar_key="a"),
        ],
    )
    assert (result.added, set(result.avatars_needed)) == (2, {FOUNDER, ADMIN})
    assert await service.set_avatar(GUILD, FOUNDER, key="a", data=WEBP)

    founder, admin = await service.directory(GUILD)  # founders first
    assert (founder.name, founder.role, founder.player_slug) == (
        "kaero.",
        "founder",
        "kaero-5734378",
    )
    assert founder.avatar_data_uri == "data:image/webp;base64," + base64.b64encode(WEBP).decode()
    assert (admin.name, admin.role, admin.player_slug, admin.avatar_data_uri) == (
        "Admin Nick",  # not linked: the server display name
        "admin",
        None,
        None,
    )
    assert str(FOUNDER) not in repr(founder) and str(ADMIN) not in repr(admin)


async def test_sync_is_idempotent_and_follows_role_nick_and_avatar_changes(
    session: AsyncSession,
) -> None:
    service = StaffService(session)
    await service.sync(GUILD, [StaffHolder(ADMIN, "Ace", "admin", avatar_key="a")])
    assert await service.set_avatar(GUILD, ADMIN, key="a", data=PNG)

    again = await service.sync(GUILD, [StaffHolder(ADMIN, "Ace", "admin", avatar_key="a")])
    assert not again.changed and again.avatars_needed == ()  # nothing to re-download

    moved = await service.sync(GUILD, [StaffHolder(ADMIN, "Ace II", "founder", avatar_key="b")])
    assert moved.updated == 1 and moved.avatars_needed == (ADMIN,)
    (entry,) = await service.directory(GUILD)
    assert (entry.name, entry.role) == ("Ace II", "founder")

    default = await service.sync(GUILD, [StaffHolder(ADMIN, "Ace II", "founder", avatar_key=None)])
    assert default.changed
    assert (await service.directory(GUILD))[0].avatar_data_uri is None

    gone = await service.sync(GUILD, [])
    assert gone.deactivated == 1 and await service.directory(GUILD) == []


async def test_ordering_and_unknown_roles(session: AsyncSession) -> None:
    service = StaffService(session)
    await service.sync(
        GUILD,
        [
            StaffHolder(1, "Second admin", "admin", position=1),
            StaffHolder(2, "First admin", "admin", position=0),
            StaffHolder(3, "Founder", "founder", position=0),
            StaffHolder(OTHER, "Moderator", "moderator"),  # not shown on the page
        ],
    )
    assert [e.name for e in await service.directory(GUILD)] == [
        "Founder",
        "First admin",
        "Second admin",
    ]


async def test_set_avatar_refuses_non_images_and_oversized_files(session: AsyncSession) -> None:
    service = StaffService(session)
    await service.sync(GUILD, [StaffHolder(ADMIN, "Ace", "admin", avatar_key="a")])
    assert not await service.set_avatar(GUILD, ADMIN, key="a", data=b"<html>")
    assert not await service.set_avatar(
        GUILD, ADMIN, key="a", data=PNG + b"\x00" * MAX_AVATAR_BYTES
    )
    assert not await service.set_avatar(GUILD, OTHER, key="a", data=PNG)  # not staff
    assert (await service.directory(GUILD))[0].avatar_data_uri is None
