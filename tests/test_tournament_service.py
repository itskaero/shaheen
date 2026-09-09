"""TournamentService: registration, bracket start, advancement, resolution."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ShaheenError
from database.models.match import MatchKind, MatchSide
from database.models.tournament import TournamentMatchStatus, TournamentStatus
from services.match_service import MatchService
from services.tournament_service import TournamentService

GUILD_ID = 1


async def _create_and_register(
    service: TournamentService, *, kind: MatchKind, discord_ids: list[int]
) -> int:
    tournament = await service.create_tournament(
        guild_id=GUILD_ID,
        name="Test Cup",
        kind=kind,
        creator_discord_id=1,
        creator_joined_at=None,
    )
    for discord_id in discord_ids:
        await service.register(
            tournament_id=tournament.id, guild_id=GUILD_ID, discord_ids=[(discord_id, None)]
        )
    return tournament.id


async def test_start_requires_at_least_two_entrants(session: AsyncSession) -> None:
    service = TournamentService(session)
    tournament_id = await _create_and_register(service, kind=MatchKind.ONE_V_ONE, discord_ids=[10])
    with pytest.raises(ShaheenError):
        await service.start_tournament(tournament_id)


async def test_register_after_start_is_rejected(session: AsyncSession) -> None:
    service = TournamentService(session)
    tournament_id = await _create_and_register(
        service, kind=MatchKind.ONE_V_ONE, discord_ids=[10, 11]
    )
    await service.start_tournament(tournament_id)
    with pytest.raises(ShaheenError):
        await service.register(
            tournament_id=tournament_id, guild_id=GUILD_ID, discord_ids=[(12, None)]
        )


async def test_register_rejects_wrong_entrant_size(session: AsyncSession) -> None:
    service = TournamentService(session)
    tournament = await service.create_tournament(
        guild_id=GUILD_ID,
        name="Duos",
        kind=MatchKind.TWO_V_TWO,
        creator_discord_id=1,
        creator_joined_at=None,
    )
    with pytest.raises(ShaheenError):
        await service.register(
            tournament_id=tournament.id, guild_id=GUILD_ID, discord_ids=[(10, None)]
        )


async def test_register_rejects_double_registration(session: AsyncSession) -> None:
    service = TournamentService(session)
    tournament_id = await _create_and_register(service, kind=MatchKind.ONE_V_ONE, discord_ids=[10])
    with pytest.raises(ShaheenError):
        await service.register(
            tournament_id=tournament_id, guild_id=GUILD_ID, discord_ids=[(10, None)]
        )


async def test_two_entrant_tournament_completes_after_one_report(session: AsyncSession) -> None:
    tournament_service = TournamentService(session)
    match_service = MatchService(session)
    tournament_id = await _create_and_register(
        tournament_service, kind=MatchKind.ONE_V_ONE, discord_ids=[10, 11]
    )
    tournament = await tournament_service.start_tournament(tournament_id)
    assert tournament.status is TournamentStatus.IN_PROGRESS

    bracket_matches = await _bracket_matches(session, tournament_id)
    assert len(bracket_matches) == 1
    final = bracket_matches[0]
    assert final.status is TournamentMatchStatus.AWAITING_REPORT
    assert final.match_id is not None

    await match_service.report_result(
        match_id=final.match_id, guild_id=GUILD_ID, reporter_discord_id=10, reporter_won=True
    )
    match = await match_service.confirm_result(
        match_id=final.match_id, guild_id=GUILD_ID, confirmer_discord_id=11
    )

    bracket_match = await tournament_service.get_bracket_match_for(final.match_id)
    assert bracket_match is not None
    result = await tournament_service.advance_from_match(
        bracket_match, winning_side=match.winning_side
    )
    assert result.tournament_completed is True

    finished = await tournament_service.get_tournament(tournament_id)
    assert finished is not None
    assert finished.status is TournamentStatus.COMPLETED


async def test_three_entrant_bracket_gives_seed_one_a_bye(session: AsyncSession) -> None:
    service = TournamentService(session)
    tournament_id = await _create_and_register(
        service, kind=MatchKind.ONE_V_ONE, discord_ids=[10, 11, 12]
    )
    await service.start_tournament(tournament_id)

    round1 = await _bracket_matches(session, tournament_id, round_number=1)
    byes = [m for m in round1 if m.status is TournamentMatchStatus.BYE]
    real = [m for m in round1 if m.status is TournamentMatchStatus.AWAITING_REPORT]
    assert len(byes) == 1
    assert len(real) == 1

    round2 = await _bracket_matches(session, tournament_id, round_number=2)
    assert len(round2) == 1
    # only the bye winner is known yet; the real match hasn't been played
    assert round2[0].status is TournamentMatchStatus.PENDING
    assert (round2[0].entrant_a_id is not None) != (round2[0].entrant_b_id is not None)


async def test_five_entrant_bracket_chains_two_byes_into_one_ready_match(
    session: AsyncSession,
) -> None:
    """Regression guard: two round-1 byes feeding the same round-2 slot must
    immediately produce a playable (AWAITING_REPORT) match, not get stuck."""
    service = TournamentService(session)
    tournament_id = await _create_and_register(
        service, kind=MatchKind.ONE_V_ONE, discord_ids=[10, 11, 12, 13, 14]
    )
    await service.start_tournament(tournament_id)

    round2 = await _bracket_matches(session, tournament_id, round_number=2)
    ready_slots = [m for m in round2 if m.status is TournamentMatchStatus.AWAITING_REPORT]
    assert len(ready_slots) == 1
    assert ready_slots[0].match_id is not None


async def test_full_four_entrant_tournament_to_completion(session: AsyncSession) -> None:
    tournament_service = TournamentService(session)
    match_service = MatchService(session)
    tournament_id = await _create_and_register(
        tournament_service, kind=MatchKind.ONE_V_ONE, discord_ids=[10, 11, 12, 13]
    )
    await tournament_service.start_tournament(tournament_id)

    # Play both round-1 matches.
    round1 = await _bracket_matches(session, tournament_id, round_number=1)
    assert len(round1) == 2

    for bracket_match in round1:
        assert bracket_match.match_id is not None
        side_a_ids = await _side_discord_id(session, bracket_match.match_id, MatchSide.A)
        match = await match_service.report_result(
            match_id=bracket_match.match_id,
            guild_id=GUILD_ID,
            reporter_discord_id=side_a_ids,
            reporter_won=True,
        )
        confirming_side = await match_service.confirming_side(match)
        assert confirming_side is not None
        confirmer_id = await _side_discord_id(session, bracket_match.match_id, confirming_side)
        confirmed = await match_service.confirm_result(
            match_id=bracket_match.match_id, guild_id=GUILD_ID, confirmer_discord_id=confirmer_id
        )
        refreshed_bracket_match = await tournament_service.get_bracket_match_for(
            bracket_match.match_id
        )
        assert refreshed_bracket_match is not None
        await tournament_service.advance_from_match(
            refreshed_bracket_match, winning_side=confirmed.winning_side
        )

    round2 = await _bracket_matches(session, tournament_id, round_number=2)
    (final,) = round2
    assert final.status is TournamentMatchStatus.AWAITING_REPORT
    assert final.match_id is not None

    side_a_id = await _side_discord_id(session, final.match_id, MatchSide.A)
    match = await match_service.report_result(
        match_id=final.match_id, guild_id=GUILD_ID, reporter_discord_id=side_a_id, reporter_won=True
    )
    confirming_side = await match_service.confirming_side(match)
    assert confirming_side is not None
    confirmer_id = await _side_discord_id(session, final.match_id, confirming_side)
    confirmed = await match_service.confirm_result(
        match_id=final.match_id, guild_id=GUILD_ID, confirmer_discord_id=confirmer_id
    )
    bracket_match = await tournament_service.get_bracket_match_for(final.match_id)
    assert bracket_match is not None
    result = await tournament_service.advance_from_match(
        bracket_match, winning_side=confirmed.winning_side
    )
    assert result.tournament_completed is True


async def test_resolve_bracket_match_advances_without_confirmation(session: AsyncSession) -> None:
    tournament_service = TournamentService(session)
    tournament_id = await _create_and_register(
        tournament_service, kind=MatchKind.ONE_V_ONE, discord_ids=[10, 11]
    )
    await tournament_service.start_tournament(tournament_id)
    (final,) = await _bracket_matches(session, tournament_id, round_number=1)

    result = await tournament_service.resolve_bracket_match(
        tournament_match_id=final.id,
        guild_id=GUILD_ID,
        resolver_discord_id=999,
        winning_side=MatchSide.A,
    )
    assert result.tournament_completed is True


async def test_resolve_unknown_bracket_match_raises(session: AsyncSession) -> None:
    tournament_service = TournamentService(session)
    with pytest.raises(NotFoundError):
        await tournament_service.resolve_bracket_match(
            tournament_match_id=99999,
            guild_id=GUILD_ID,
            resolver_discord_id=999,
            winning_side=MatchSide.A,
        )


async def _bracket_matches(
    session: AsyncSession, tournament_id: int, *, round_number: int | None = None
):
    from database.repositories.tournament_repository import TournamentMatchRepository

    repo = TournamentMatchRepository(session)
    if round_number is None:
        return await repo.list_all(tournament_id)
    return await repo.list_for_round(tournament_id, round_number)


async def _side_discord_id(session: AsyncSession, match_id: int, side: MatchSide) -> int:
    from database.repositories.match_repository import MatchRepository

    ids = await MatchRepository(session).discord_ids_on_side(match_id, side)
    return ids[0]
