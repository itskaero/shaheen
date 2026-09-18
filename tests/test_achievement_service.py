"""AchievementService: the single award seam introduced in ADR-081.

Before this existed, link_service and snapshot_service each hand-rolled the
same "look up catalog row -> award" dance, and the `extra` JSON column was
declared but never written by anything.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.member_achievement import MemberAchievement
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from services.achievement_service import AchievementService
from services.achievements import FIRST_LINK, GAMES_100, GAMES_500, AchievementDef

GUILD_ID = 1


async def _member_id(session: AsyncSession) -> int:
    user = await DiscordUserRepository(session).get_or_create(1)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD_ID
    )
    return member.id


async def test_award_records_the_context_that_earned_it(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    member_id = await _member_id(session)

    awarded = await AchievementService(session).award(
        shaheen_member_id=member_id, definition=GAMES_100, extra={"games": 143}
    )

    assert awarded is not None
    row = (await session.execute(select(MemberAchievement))).scalars().one()
    assert row.extra == {"games": 143}


async def test_award_is_idempotent(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    member_id = await _member_id(session)
    service = AchievementService(session)

    assert await service.award(shaheen_member_id=member_id, definition=GAMES_100) is not None
    assert await service.award(shaheen_member_id=member_id, definition=GAMES_100) is None

    rows = (await session.execute(select(MemberAchievement))).scalars().all()
    assert len(rows) == 1


async def test_award_many_returns_only_what_was_newly_granted(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    member_id = await _member_id(session)
    service = AchievementService(session)
    await service.award(shaheen_member_id=member_id, definition=GAMES_100)

    granted = await service.award_many(
        shaheen_member_id=member_id, definitions=(GAMES_100, GAMES_500)
    )

    assert granted == [GAMES_500]


async def test_earned_keys_reflects_awards(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    member_id = await _member_id(session)
    service = AchievementService(session)
    assert await service.earned_keys(member_id) == set()

    await service.award(shaheen_member_id=member_id, definition=FIRST_LINK)
    assert await service.earned_keys(member_id) == {FIRST_LINK.key}


async def test_award_of_an_uncatalogued_key_is_skipped_not_raised(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    """A catalog miss means the deploy is mid-migration — never block the
    caller's real work (a match result, a snapshot) over a missing badge.
    """
    member_id = await _member_id(session)
    unknown = AchievementDef("not_in_catalog", "Ghost", "Not seeded anywhere.", "milestone")

    assert (
        await AchievementService(session).award(shaheen_member_id=member_id, definition=unknown)
        is None
    )
    assert (await session.execute(select(MemberAchievement))).scalars().all() == []
