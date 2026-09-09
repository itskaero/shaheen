"""DiscordUser/ShaheenMember/BrawlhallaPlayer/MemberPlayerLink repositories."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository


async def test_discord_user_get_or_create_is_idempotent(session: AsyncSession) -> None:
    repo = DiscordUserRepository(session)
    first = await repo.get_or_create(42)
    second = await repo.get_or_create(42)
    assert first.id == second.id


async def test_shaheen_member_scoped_per_guild(session: AsyncSession) -> None:
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    user = await users.get_or_create(42)

    member_a = await members.get_or_create(discord_user_id=user.id, guild_id=1)
    member_b = await members.get_or_create(discord_user_id=user.id, guild_id=2)
    assert member_a.id != member_b.id

    again = await members.get_or_create(discord_user_id=user.id, guild_id=1)
    assert again.id == member_a.id


async def test_brawlhalla_player_upsert_updates_name(session: AsyncSession) -> None:
    repo = BrawlhallaPlayerRepository(session)
    created = await repo.upsert(brawlhalla_player_id=1, player_name="Old", region="us-e")
    updated = await repo.upsert(brawlhalla_player_id=1, player_name="New", region="eu")

    assert created.id == updated.id
    assert updated.player_name == "New"
    assert updated.region == "eu"


async def test_member_player_link_active_lookup_and_unlink(session: AsyncSession) -> None:
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)
    links = MemberPlayerLinkRepository(session)

    user = await users.get_or_create(1)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=1)
    player = await players.upsert(brawlhalla_player_id=100, player_name="P", region=None)

    assert await links.get_active(member.id) is None

    link = await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
    assert link.unlinked_at is None
    active = await links.get_active(member.id)
    assert active is not None
    assert active.id == link.id

    unlinked = await links.unlink(member.id)
    assert unlinked is not None
    assert unlinked.unlinked_at is not None
    assert await links.get_active(member.id) is None


async def test_relinking_unlinks_previous_active_link(session: AsyncSession) -> None:
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)
    links = MemberPlayerLinkRepository(session)

    user = await users.get_or_create(1)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=1)
    player_a = await players.upsert(brawlhalla_player_id=100, player_name="A", region=None)
    player_b = await players.upsert(brawlhalla_player_id=200, player_name="B", region=None)

    first = await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player_a.id)
    second = await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player_b.id)

    await session.refresh(first)
    assert first.unlinked_at is not None
    active = await links.get_active(member.id)
    assert active is not None
    assert active.id == second.id


async def test_only_one_active_link_per_member_at_db_level(session: AsyncSession) -> None:
    """Regression guard for the partial unique index, bypassing the repository's own guard."""
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)

    user = await users.get_or_create(1)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=1)
    player_a = await players.upsert(brawlhalla_player_id=100, player_name="A", region=None)
    player_b = await players.upsert(brawlhalla_player_id=200, player_name="B", region=None)

    from datetime import UTC, datetime

    from database.models.member_player_link import MemberPlayerLink

    session.add(
        MemberPlayerLink(
            shaheen_member_id=member.id,
            brawlhalla_player_id=player_a.id,
            linked_at=datetime.now(UTC),
        )
    )
    await session.flush()

    session.add(
        MemberPlayerLink(
            shaheen_member_id=member.id,
            brawlhalla_player_id=player_b.id,
            linked_at=datetime.now(UTC),
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
    else:
        raise AssertionError("Expected the partial unique index to reject a second active link")
