"""Coaching: the coach directory and requests (docs/DECISIONS.md ADR-126)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.content.coaching_embeds import (
    build_coach_list_embed,
    build_request_card,
)
from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ShaheenError
from database.models.audit_log import AuditLogEntry
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from services.coaching_service import (
    MAX_OPEN_PER_STUDENT,
    CoachingService,
    RoleHolder,
    clean_legends,
    parse_legends,
)

GUILD = 1
COACH, OTHER_COACH, STUDENT, STAFF = 100, 101, 200, 300
NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


async def _link(session: AsyncSession, discord_id: int, brawlhalla_id: int, name: str) -> None:
    user = await DiscordUserRepository(session).get_or_create(discord_id)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD
    )
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=brawlhalla_id, player_name=name, region="us-e"
    )
    await MemberPlayerLinkRepository(session).link(
        shaheen_member_id=member.id, brawlhalla_player_id=player.id
    )


async def _coaches(session: AsyncSession, *ids: int) -> CoachingService:
    service = CoachingService(session)
    await service.sync(GUILD, [RoleHolder(i, f"Coach{i}") for i in ids])
    return service


def test_legends_are_normalised_deduplicated_and_capped() -> None:
    assert clean_legends("Bödvar, lord vraxx, bodvar") == "bodvar,lord_vraxx"
    assert clean_legends("  ") is None
    assert parse_legends("bodvar,lord_vraxx") == ["bodvar", "lord_vraxx"]
    assert parse_legends(None) == []
    with pytest.raises(ShaheenError):
        clean_legends("a, b, c, d")
    with pytest.raises(ShaheenError):
        clean_legends("<script>")


async def test_sync_mirrors_the_role_and_keeps_history(session: AsyncSession) -> None:
    await _link(session, COACH, 10, "Ace")
    service = CoachingService(session)

    first = await service.sync(GUILD, [RoleHolder(COACH, "Ace"), RoleHolder(OTHER_COACH, "Bo")])
    assert (first.added, first.deactivated) == (2, 0)
    assert (
        await service.sync(GUILD, [RoleHolder(COACH, "Ace"), RoleHolder(OTHER_COACH, "Bo")])
    ).changed is False

    coach = await service.coach_of(GUILD, COACH)
    assert coach is not None and coach.brawlhalla_player_id is not None  # linked
    assert (await service.coach_of(GUILD, OTHER_COACH)).brawlhalla_player_id is None  # type: ignore[union-attr]

    lost = await service.sync(GUILD, [RoleHolder(COACH, "Ace")])
    assert lost.deactivated == 1
    assert await service.coach_of(GUILD, OTHER_COACH) is None
    back = await service.sync(GUILD, [RoleHolder(COACH, "Ace"), RoleHolder(OTHER_COACH, "Bo")])
    assert back.reactivated == 1


async def test_profile_updates_and_clears(session: AsyncSession) -> None:
    service = await _coaches(session, COACH)
    coach = await service.coach_of(GUILD, COACH)
    assert coach is not None
    await service.update_profile(
        coach, specialty="  Sword   basics ", legends="Hattori, Koji", accepting=False
    )
    assert (coach.specialty, coach.legends, coach.accepting) == (
        "Sword basics",
        "hattori,koji",
        False,
    )
    await service.update_profile(coach, specialty="")
    assert coach.specialty is None


async def test_request_rules(session: AsyncSession) -> None:
    service = await _coaches(session, COACH, OTHER_COACH)
    with pytest.raises(NotFoundError):
        await service.request(
            guild_id=GUILD, coach_discord_id=STUDENT, student_discord_id=COACH, message="x" * 20
        )
    with pytest.raises(ShaheenError):
        await service.request(
            guild_id=GUILD, coach_discord_id=COACH, student_discord_id=COACH, message="x" * 20
        )
    with pytest.raises(ShaheenError):  # too short once cleaned
        await service.request(
            guild_id=GUILD, coach_discord_id=COACH, student_discord_id=STUDENT, message="  hi   "
        )

    request, coach = await service.request(
        guild_id=GUILD,
        coach_discord_id=COACH,
        student_discord_id=STUDENT,
        message="Help with Scythe combos please",
        now=NOW,
    )
    assert (request.status, coach.discord_id) == ("open", COACH)
    with pytest.raises(ConflictError):  # one open request per coach
        await service.request(
            guild_id=GUILD,
            coach_discord_id=COACH,
            student_discord_id=STUDENT,
            message="Asking again, sorry!",
            now=NOW,
        )
    # A lapsed request doesn't block a new one.
    again, _ = await service.request(
        guild_id=GUILD,
        coach_discord_id=COACH,
        student_discord_id=STUDENT,
        message="Asking again a week later",
        now=NOW + timedelta(days=8),
    )
    assert again.id != request.id


async def test_a_paused_coach_takes_no_requests(session: AsyncSession) -> None:
    service = await _coaches(session, COACH)
    coach = await service.coach_of(GUILD, COACH)
    assert coach is not None
    await service.update_profile(coach, accepting=False)
    with pytest.raises(ConflictError):
        await service.request(
            guild_id=GUILD, coach_discord_id=COACH, student_discord_id=STUDENT, message="x" * 20
        )


async def test_open_requests_per_student_are_capped(session: AsyncSession) -> None:
    ids = list(range(500, 500 + MAX_OPEN_PER_STUDENT + 1))
    service = await _coaches(session, *ids)
    for coach_id in ids[:MAX_OPEN_PER_STUDENT]:
        await service.request(
            guild_id=GUILD, coach_discord_id=coach_id, student_discord_id=STUDENT, message="x" * 20
        )
    with pytest.raises(ConflictError):
        await service.request(
            guild_id=GUILD, coach_discord_id=ids[-1], student_discord_id=STUDENT, message="x" * 20
        )


async def test_only_the_coach_or_staff_answer_once(session: AsyncSession) -> None:
    service = await _coaches(session, COACH, OTHER_COACH)
    request, _ = await service.request(
        guild_id=GUILD, coach_discord_id=COACH, student_discord_id=STUDENT, message="x" * 20
    )
    with pytest.raises(PermissionDeniedError):
        await service.respond(
            request_id=request.id, actor_discord_id=OTHER_COACH, accept=True, is_staff=False
        )
    answered, coach = await service.respond(
        request_id=request.id, actor_discord_id=COACH, accept=True, is_staff=False
    )
    assert answered.status == "accepted" and answered.responded_at is not None
    with pytest.raises(ConflictError):
        await service.respond(
            request_id=request.id, actor_discord_id=STAFF, accept=False, is_staff=True
        )

    other, _ = await service.request(
        guild_id=GUILD, coach_discord_id=OTHER_COACH, student_discord_id=STUDENT, message="y" * 20
    )
    declined, _ = await service.respond(
        request_id=other.id, actor_discord_id=STAFF, accept=False, is_staff=True
    )
    assert declined.status == "declined"
    with pytest.raises(NotFoundError):
        await service.respond(request_id=999, actor_discord_id=COACH, accept=True, is_staff=True)

    actions = set((await session.execute(select(AuditLogEntry.action))).scalars().all())
    assert {"coaching.request", "coaching.accept", "coaching.decline"} <= actions


async def test_a_lapsed_request_cant_be_answered(session: AsyncSession) -> None:
    service = await _coaches(session, COACH)
    request, _ = await service.request(
        guild_id=GUILD,
        coach_discord_id=COACH,
        student_discord_id=STUDENT,
        message="x" * 20,
        now=NOW,
    )
    with pytest.raises(ConflictError):
        await service.respond(
            request_id=request.id,
            actor_discord_id=COACH,
            accept=True,
            is_staff=False,
            now=NOW + timedelta(days=8),
        )


async def test_directory_puts_accepting_coaches_with_sessions_first(
    session: AsyncSession,
) -> None:
    service = await _coaches(session, COACH, OTHER_COACH)
    paused = await service.coach_of(GUILD, OTHER_COACH)
    assert paused is not None
    await service.update_profile(paused, accepting=False)
    request, _ = await service.request(
        guild_id=GUILD, coach_discord_id=COACH, student_discord_id=STUDENT, message="x" * 20
    )
    await service.respond(
        request_id=request.id, actor_discord_id=COACH, accept=True, is_staff=False
    )

    entries = await service.directory(GUILD)
    assert [(e.coach.discord_id, e.sessions) for e in entries] == [(COACH, 1), (OTHER_COACH, 0)]
    embed = build_coach_list_embed(entries, site_url="https://example.org/")
    assert f"<@{COACH}>" in (embed.description or "")
    card = build_request_card(request, entries[0].coach)
    assert card.title == f"🎓 Coaching request #{request.id}"


def test_empty_directory_embed_says_how_to_add_coaches() -> None:
    embed = build_coach_list_embed([], site_url="https://example.org")
    assert "Coach role" in (embed.description or "")
