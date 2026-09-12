"""MatchService: challenges, scrims, ad-hoc matches, report/confirm/dispute/resolve."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, PermissionDeniedError, ShaheenError
from database.models.match import MatchKind, MatchSide, MatchStatus
from database.models.scrim import ScrimStatus
from services.match_service import MatchService, RivalryResult

GUILD_ID = 1


async def test_challenge_self_is_rejected(session: AsyncSession) -> None:
    service = MatchService(session)
    with pytest.raises(ShaheenError):
        await service.create_challenge(
            guild_id=GUILD_ID,
            challenger_discord_id=1,
            challenger_joined_at=None,
            opponent_discord_id=1,
            opponent_joined_at=None,
        )


async def test_challenge_accept_creates_1v1_match(session: AsyncSession) -> None:
    service = MatchService(session)
    challenge = await service.create_challenge(
        guild_id=GUILD_ID,
        challenger_discord_id=1,
        challenger_joined_at=None,
        opponent_discord_id=2,
        opponent_joined_at=None,
    )
    match = await service.accept_challenge(challenge.id)
    assert match.kind is MatchKind.ONE_V_ONE
    assert match.status is MatchStatus.PENDING_CONFIRMATION


async def test_challenge_decline_does_not_create_a_match(session: AsyncSession) -> None:
    service = MatchService(session)
    challenge = await service.create_challenge(
        guild_id=GUILD_ID,
        challenger_discord_id=1,
        challenger_joined_at=None,
        opponent_discord_id=2,
        opponent_joined_at=None,
    )
    await service.decline_challenge(challenge.id)
    assert challenge.status.value == "declined"


async def test_scrim_1v1_fills_and_creates_match(session: AsyncSession) -> None:
    service = MatchService(session)
    scrim = await service.create_scrim(
        guild_id=GUILD_ID, creator_discord_id=1, creator_joined_at=None, kind=MatchKind.ONE_V_ONE
    )

    first = await service.join_scrim(
        scrim_id=scrim.id, discord_id=2, joined_at=None, side=MatchSide.A
    )
    assert first.match is None
    assert first.side_counts == (1, 0)

    second = await service.join_scrim(
        scrim_id=scrim.id, discord_id=3, joined_at=None, side=MatchSide.B
    )
    assert second.match is not None
    assert scrim.status is ScrimStatus.FULL


async def test_scrim_rejects_duplicate_signup(session: AsyncSession) -> None:
    service = MatchService(session)
    scrim = await service.create_scrim(
        guild_id=GUILD_ID, creator_discord_id=1, creator_joined_at=None, kind=MatchKind.ONE_V_ONE
    )
    await service.join_scrim(scrim_id=scrim.id, discord_id=2, joined_at=None, side=MatchSide.A)
    with pytest.raises(ShaheenError):
        await service.join_scrim(scrim_id=scrim.id, discord_id=2, joined_at=None, side=MatchSide.B)


async def test_scrim_rejects_full_side(session: AsyncSession) -> None:
    service = MatchService(session)
    scrim = await service.create_scrim(
        guild_id=GUILD_ID, creator_discord_id=1, creator_joined_at=None, kind=MatchKind.ONE_V_ONE
    )
    await service.join_scrim(scrim_id=scrim.id, discord_id=2, joined_at=None, side=MatchSide.A)
    with pytest.raises(ShaheenError):
        await service.join_scrim(scrim_id=scrim.id, discord_id=3, joined_at=None, side=MatchSide.A)


async def test_scrim_2v2_requires_two_per_side(session: AsyncSession) -> None:
    service = MatchService(session)
    scrim = await service.create_scrim(
        guild_id=GUILD_ID, creator_discord_id=1, creator_joined_at=None, kind=MatchKind.TWO_V_TWO
    )
    for discord_id, side in ((2, MatchSide.A), (3, MatchSide.A), (4, MatchSide.B)):
        result = await service.join_scrim(
            scrim_id=scrim.id, discord_id=discord_id, joined_at=None, side=side
        )
        assert result.match is None
    final = await service.join_scrim(
        scrim_id=scrim.id, discord_id=5, joined_at=None, side=MatchSide.B
    )
    assert final.match is not None
    assert final.match.kind is MatchKind.TWO_V_TWO


async def test_create_match_rejects_wrong_side_size(session: AsyncSession) -> None:
    service = MatchService(session)
    with pytest.raises(ShaheenError):
        await service.create_match(
            guild_id=GUILD_ID,
            kind=MatchKind.TWO_V_TWO,
            side_a=[(1, None)],
            side_b=[(2, None)],
        )


async def test_create_match_rejects_overlapping_players(session: AsyncSession) -> None:
    service = MatchService(session)
    with pytest.raises(ShaheenError):
        await service.create_match(
            guild_id=GUILD_ID,
            kind=MatchKind.ONE_V_ONE,
            side_a=[(1, None)],
            side_b=[(1, None)],
        )


async def test_report_confirm_dispute_resolve_flow(session: AsyncSession) -> None:
    service = MatchService(session)
    match = await service.create_match(
        guild_id=GUILD_ID, kind=MatchKind.ONE_V_ONE, side_a=[(1, None)], side_b=[(2, None)]
    )

    # only a participant may report
    with pytest.raises(PermissionDeniedError):
        await service.report_result(
            match_id=match.id, guild_id=GUILD_ID, reporter_discord_id=999, reporter_won=True
        )

    reported = await service.report_result(
        match_id=match.id, guild_id=GUILD_ID, reporter_discord_id=1, reporter_won=True
    )
    assert reported.reported_winning_side is MatchSide.A

    # the reporter's own side can't confirm their own claim
    with pytest.raises(PermissionDeniedError):
        await service.confirm_result(match_id=match.id, guild_id=GUILD_ID, confirmer_discord_id=1)

    confirmed = await service.confirm_result(
        match_id=match.id, guild_id=GUILD_ID, confirmer_discord_id=2
    )
    assert confirmed.status is MatchStatus.CONFIRMED
    assert confirmed.winning_side is MatchSide.A


async def test_dispute_leaves_match_disputed_until_staff_resolves(session: AsyncSession) -> None:
    service = MatchService(session)
    match = await service.create_match(
        guild_id=GUILD_ID, kind=MatchKind.ONE_V_ONE, side_a=[(1, None)], side_b=[(2, None)]
    )
    await service.report_result(
        match_id=match.id, guild_id=GUILD_ID, reporter_discord_id=1, reporter_won=True
    )
    disputed = await service.dispute_result(
        match_id=match.id, guild_id=GUILD_ID, disputer_discord_id=2
    )
    assert disputed.status.value == "disputed"

    resolved = await service.resolve_result(
        match_id=match.id, guild_id=GUILD_ID, resolver_discord_id=999, winning_side=MatchSide.B
    )
    assert resolved.status is MatchStatus.CONFIRMED
    assert resolved.winning_side is MatchSide.B


async def test_report_unknown_match_raises_not_found(session: AsyncSession) -> None:
    service = MatchService(session)
    with pytest.raises(NotFoundError):
        await service.report_result(
            match_id=12345, guild_id=GUILD_ID, reporter_discord_id=1, reporter_won=True
        )


async def test_match_history_returns_recent_matches_for_participant(session: AsyncSession) -> None:
    service = MatchService(session)
    await service.create_match(
        guild_id=GUILD_ID, kind=MatchKind.ONE_V_ONE, side_a=[(1, None)], side_b=[(2, None)]
    )
    history = await service.get_match_history(guild_id=GUILD_ID, discord_id=1)
    assert len(history) == 1

    other_history = await service.get_match_history(guild_id=GUILD_ID, discord_id=999)
    assert other_history == []


async def _confirmed_match(
    service: MatchService, *, winner_discord_id: int, loser_discord_id: int
) -> None:
    match = await service.create_match(
        guild_id=GUILD_ID,
        kind=MatchKind.ONE_V_ONE,
        side_a=[(winner_discord_id, None)],
        side_b=[(loser_discord_id, None)],
    )
    await service.report_result(
        match_id=match.id,
        guild_id=GUILD_ID,
        reporter_discord_id=winner_discord_id,
        reporter_won=True,
    )
    await service.confirm_result(
        match_id=match.id, guild_id=GUILD_ID, confirmer_discord_id=loser_discord_id
    )


async def test_head_to_head_tallies_confirmed_wins_each_way(session: AsyncSession) -> None:
    service = MatchService(session)
    await _confirmed_match(service, winner_discord_id=1, loser_discord_id=2)
    await _confirmed_match(service, winner_discord_id=1, loser_discord_id=2)
    await _confirmed_match(service, winner_discord_id=2, loser_discord_id=1)

    result = await service.head_to_head(guild_id=GUILD_ID, discord_id_a=1, discord_id_b=2)
    assert result.member_a_wins == 2
    assert result.member_b_wins == 1
    assert result.total_matches == 3

    # Symmetric from the other direction.
    reversed_result = await service.head_to_head(guild_id=GUILD_ID, discord_id_a=2, discord_id_b=1)
    assert reversed_result.member_a_wins == 1
    assert reversed_result.member_b_wins == 2


async def test_head_to_head_ignores_unconfirmed_matches(session: AsyncSession) -> None:
    service = MatchService(session)
    match = await service.create_match(
        guild_id=GUILD_ID, kind=MatchKind.ONE_V_ONE, side_a=[(1, None)], side_b=[(2, None)]
    )
    await service.report_result(
        match_id=match.id, guild_id=GUILD_ID, reporter_discord_id=1, reporter_won=True
    )
    # never confirmed

    result = await service.head_to_head(guild_id=GUILD_ID, discord_id_a=1, discord_id_b=2)
    assert result.total_matches == 0


async def test_head_to_head_zero_for_members_who_never_played(session: AsyncSession) -> None:
    service = MatchService(session)
    result = await service.head_to_head(guild_id=GUILD_ID, discord_id_a=1, discord_id_b=2)
    assert result == RivalryResult(member_a_wins=0, member_b_wins=0, total_matches=0)


async def test_head_to_head_only_counts_matches_against_each_other(session: AsyncSession) -> None:
    """A confirmed match against a third member shouldn't count toward
    the rivalry between member_a and member_b.
    """
    service = MatchService(session)
    await _confirmed_match(service, winner_discord_id=1, loser_discord_id=2)
    await _confirmed_match(service, winner_discord_id=1, loser_discord_id=999)

    result = await service.head_to_head(guild_id=GUILD_ID, discord_id_a=1, discord_id_b=2)
    assert result.total_matches == 1
