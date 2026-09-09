"""Direct repository tests for Match/Challenge/Scrim/Tournament tables."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.match import MatchKind, MatchSide
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.challenge_repository import ChallengeRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.match_repository import MatchRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.tournament_repository import (
    TournamentEntrantRepository,
    TournamentMatchRepository,
    TournamentRepository,
)


async def _member(session: AsyncSession, discord_id: int, guild_id: int = 1) -> int:
    user = await DiscordUserRepository(session).get_or_create(discord_id)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=guild_id
    )
    return member.id


async def test_match_repository_create_and_participants(session: AsyncSession) -> None:
    m1 = await _member(session, 1)
    m2 = await _member(session, 2)
    repo = MatchRepository(session)

    match = await repo.create(
        guild_id=1, kind=MatchKind.ONE_V_ONE, participants=[(m1, MatchSide.A), (m2, MatchSide.B)]
    )
    assert await repo.is_participant(match.id, m1) is MatchSide.A
    assert await repo.is_participant(match.id, m2) is MatchSide.B
    assert await repo.is_participant(match.id, 99999) is None

    ids_a = await repo.discord_ids_on_side(match.id, MatchSide.A)
    assert ids_a == [1]


async def test_match_repository_report_confirm(session: AsyncSession) -> None:
    m1 = await _member(session, 1)
    m2 = await _member(session, 2)
    repo = MatchRepository(session)
    match = await repo.create(
        guild_id=1, kind=MatchKind.ONE_V_ONE, participants=[(m1, MatchSide.A), (m2, MatchSide.B)]
    )

    await repo.report(match, reported_by_member_id=m1, winning_side=MatchSide.A)
    assert match.reported_winning_side is MatchSide.A
    assert match.winning_side is None

    await repo.confirm(match)
    assert match.winning_side is MatchSide.A
    assert match.confirmed_at is not None


async def test_challenge_repository_accept_flow(session: AsyncSession) -> None:
    m1 = await _member(session, 1)
    m2 = await _member(session, 2)
    repo = ChallengeRepository(session)
    challenge = await repo.create(guild_id=1, challenger_member_id=m1, opponent_member_id=m2)
    assert challenge.status.value == "pending"

    await repo.accept(challenge, match_id=42)
    assert challenge.status.value == "accepted"
    assert challenge.match_id == 42
    assert challenge.responded_at is not None


async def test_tournament_entrant_registration_and_membership(session: AsyncSession) -> None:
    m1 = await _member(session, 1)
    m2 = await _member(session, 2)
    tournaments = TournamentRepository(session)
    entrants = TournamentEntrantRepository(session)

    tournament = await tournaments.create(
        guild_id=1, name="Cup", kind=MatchKind.TWO_V_TWO, created_by_member_id=m1
    )
    entrant = await entrants.register(tournament_id=tournament.id, shaheen_member_ids=[m1, m2])
    members = await entrants.members_of(entrant.id)
    assert set(members) == {m1, m2}

    assert await entrants.is_registered(tournament.id, m1) is True
    assert await entrants.is_registered(tournament.id, 99999) is False


async def test_tournament_match_slot_lookup(session: AsyncSession) -> None:
    m1 = await _member(session, 1)
    tournaments = TournamentRepository(session)
    bracket = TournamentMatchRepository(session)

    tournament = await tournaments.create(
        guild_id=1, name="Cup", kind=MatchKind.ONE_V_ONE, created_by_member_id=m1
    )
    from database.models.tournament import TournamentMatchStatus

    created = await bracket.create(
        tournament_id=tournament.id,
        round_number=1,
        slot_index=0,
        entrant_a_id=None,
        entrant_b_id=None,
        status=TournamentMatchStatus.PENDING,
    )
    fetched = await bracket.get_by_slot(tournament.id, 1, 0)
    assert fetched is not None
    assert fetched.id == created.id
    assert await bracket.get_by_slot(tournament.id, 1, 1) is None
    assert await bracket.max_round(tournament.id) == 1


async def test_brawlhalla_player_repository_still_works_with_new_models(
    session: AsyncSession,
) -> None:
    """Not a Phase 4 model, but a quick cross-check that shared tables aren't disturbed."""
    repo = BrawlhallaPlayerRepository(session)
    player = await repo.upsert(brawlhalla_player_id=1, player_name="P", region=None)
    assert await repo.get_by_id(player.id) is not None
