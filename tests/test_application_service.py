"""Membership application rules (docs/DECISIONS.md ADR-089).

The rules that matter are the ones a Discord button can't enforce on its
own: one open application at a time, a cooldown after a denial, and a
decision that can only be made once even though the card with the buttons
lives in the channel forever.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.content.application_embeds import (
    build_application_decision_dm_embed,
    build_application_review_embed,
)
from core.exceptions import NotFoundError, ShaheenError
from database.models.application import Application, ApplicationStatus
from services.application_service import (
    REAPPLY_COOLDOWN_DAYS,
    ApplicationAnswers,
    ApplicationService,
)

GUILD_ID = 1
APPLICANT = 4001
REVIEWER = 9001

ANSWERS = ApplicationAnswers(
    brawlhalla_identifier="76561198000000000",
    region="Pakistan (PKT)",
    current_rank="Platinum 2",
    motivation="I queue ranked every night and want people to review my sets with.",
    referred_by=None,
)


async def test_submit_records_the_answers(session: AsyncSession) -> None:
    application = await ApplicationService(session).submit(
        guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS
    )

    assert application.status is ApplicationStatus.PENDING
    assert application.brawlhalla_identifier == "76561198000000000"
    assert application.answers["region"] == "Pakistan (PKT)"
    assert application.attempt == 1


async def test_only_one_application_can_be_open(session: AsyncSession) -> None:
    service = ApplicationService(session)
    await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)

    with pytest.raises(ShaheenError, match="already have an application"):
        await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)


async def test_approval_grants_and_records_the_reviewer(session: AsyncSession) -> None:
    service = ApplicationService(session)
    application = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)

    await service.decide(application, approved=True, reviewer_discord_id=REVIEWER, note="Solid.")

    assert application.status is ApplicationStatus.APPROVED
    assert application.reviewer_discord_id == REVIEWER
    assert application.review_note == "Solid."
    assert application.reviewed_at is not None


async def test_an_application_can_only_be_decided_once(session: AsyncSession) -> None:
    """The review card stays in the channel forever, so a second click — or
    two staff clicking together — must not re-decide a settled application.
    """
    service = ApplicationService(session)
    application = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)
    await service.decide(application, approved=True, reviewer_discord_id=REVIEWER)

    with pytest.raises(ShaheenError, match="already approved"):
        await service.decide(application, approved=False, reviewer_discord_id=REVIEWER)


async def test_nobody_reviews_their_own_application(session: AsyncSession) -> None:
    service = ApplicationService(session)
    application = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)

    with pytest.raises(ShaheenError, match="your own application"):
        await service.decide(application, approved=True, reviewer_discord_id=APPLICANT)


async def test_denial_starts_a_cooldown(session: AsyncSession) -> None:
    service = ApplicationService(session)
    application = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)
    await service.decide(application, approved=False, reviewer_discord_id=REVIEWER)

    with pytest.raises(ShaheenError, match="apply again in"):
        await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)


async def test_reapplying_is_allowed_once_the_cooldown_expires(session: AsyncSession) -> None:
    service = ApplicationService(session)
    first = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)
    await service.decide(first, approved=False, reviewer_discord_id=REVIEWER)

    later = datetime.now(UTC) + timedelta(days=REAPPLY_COOLDOWN_DAYS + 1)
    second = await service.submit(
        guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS, now=later
    )

    assert second.status is ApplicationStatus.PENDING
    assert second.attempt == 2


async def test_an_approved_member_cannot_apply_again(session: AsyncSession) -> None:
    service = ApplicationService(session)
    application = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)
    await service.decide(application, approved=True, reviewer_discord_id=REVIEWER)

    with pytest.raises(ShaheenError, match="already been approved"):
        await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)


async def test_withdrawing_frees_the_applicant_to_apply_again(session: AsyncSession) -> None:
    service = ApplicationService(session)
    await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)

    withdrawn = await service.withdraw(guild_id=GUILD_ID, discord_id=APPLICANT)
    assert withdrawn.status is ApplicationStatus.WITHDRAWN

    again = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)
    assert again.status is ApplicationStatus.PENDING


async def test_withdrawing_nothing_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await ApplicationService(session).withdraw(guild_id=GUILD_ID, discord_id=APPLICANT)


async def test_pending_queue_is_oldest_first_and_excludes_decided(
    session: AsyncSession,
) -> None:
    service = ApplicationService(session)
    first = await service.submit(guild_id=GUILD_ID, discord_id=1, answers=ANSWERS)
    await service.submit(guild_id=GUILD_ID, discord_id=2, answers=ANSWERS)
    third = await service.submit(guild_id=GUILD_ID, discord_id=3, answers=ANSWERS)
    await service.decide(third, approved=True, reviewer_discord_id=REVIEWER)

    pending = await service.pending(GUILD_ID)

    assert [a.discord_id for a in pending] == [1, 2]
    assert pending[0].id == first.id


async def test_review_card_lookup_finds_its_application(session: AsyncSession) -> None:
    """The Approve/Deny buttons carry static custom_ids and find their
    application from the message they're attached to.
    """
    service = ApplicationService(session)
    application = await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)
    await service.attach_review_message(application, 555_000_111)
    await session.flush()

    found = await service.for_review_message(555_000_111)
    assert found is not None and found.id == application.id
    assert await service.for_review_message(404) is None


async def test_applications_are_scoped_per_guild(session: AsyncSession) -> None:
    service = ApplicationService(session)
    await service.submit(guild_id=GUILD_ID, discord_id=APPLICANT, answers=ANSWERS)

    # A pending application in one guild must not block another.
    other = await service.submit(guild_id=GUILD_ID + 1, discord_id=APPLICANT, answers=ANSWERS)
    assert other.status is ApplicationStatus.PENDING
    assert len(await service.pending(GUILD_ID)) == 1


# --- embeds: the reviewer reads untrusted free text -------------------------


def test_review_embed_clips_a_very_long_answer() -> None:
    """Applicants type into a 1000-char box; an embed field caps at 1024.
    A rejected embed would lose the card the buttons hang off, so the
    answer is clipped rather than sent whole.
    """
    application = Application(
        id=7,
        guild_id=GUILD_ID,
        discord_id=APPLICANT,
        status=ApplicationStatus.PENDING,
        answers={"region": "SEA", "current_rank": "Gold", "motivation": "x" * 4000},
        brawlhalla_identifier="123",
        attempt=1,
    )

    embed = build_application_review_embed(application)

    motivation = next(f for f in embed.fields if f.name == "Why Shaheen")
    assert motivation.value is not None
    assert len(motivation.value) <= 1024
    assert motivation.value.endswith("…")


def test_review_embed_survives_an_applicant_who_left() -> None:
    application = Application(
        id=8,
        guild_id=GUILD_ID,
        discord_id=APPLICANT,
        status=ApplicationStatus.PENDING,
        answers={"region": "SEA", "current_rank": "Gold", "motivation": "hi"},
        attempt=1,
    )

    embed = build_application_review_embed(application, applicant=None)

    assert embed.description is not None
    assert str(APPLICANT) in embed.description


def test_decision_dm_never_leaks_the_reviewer() -> None:
    """The applicant is told the outcome and any staff note — not who
    decided it, which stays internal to #applications and the mod log.
    """
    application = Application(
        id=9,
        guild_id=GUILD_ID,
        discord_id=APPLICANT,
        status=ApplicationStatus.DENIED,
        answers={},
        reviewer_discord_id=REVIEWER,
        review_note="Not enough ranked games yet.",
        attempt=1,
    )

    embed = build_application_decision_dm_embed(application, guild_name="Shaheen")

    rendered = (embed.description or "") + "".join(
        (f.name or "") + (f.value or "") for f in embed.fields
    )
    assert str(REVIEWER) not in rendered
    assert "Not enough ranked games yet." in rendered
    assert "14 days" in (embed.description or "")
