"""Website account linking: codes, claims, takeover protection, verification
(docs/DECISIONS.md ADR-107).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, InvalidCodeError, NotFoundError, RateLimitedError
from database.models.audit_log import AuditLogEntry
from database.models.link_code import LinkCode
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from services.link_code_service import (
    CODE_ALPHABET,
    LinkCodeService,
    hash_code,
    normalize_code,
)
from services.link_service import LinkService

GUILD = 1
NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)


async def _player(session: AsyncSession, bid: int = 10, name: str = "Kaero") -> int:
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=bid, player_name=name, region=None
    )
    return player.id


def test_codes_normalize_and_reject_ambiguous_characters() -> None:
    assert normalize_code(" abcd-efgh ") == "ABCDEFGH"
    assert normalize_code("ABCD EFGH") == "ABCDEFGH"
    assert normalize_code("ABCD-EFG") is None  # too short
    assert normalize_code("ABCD-EFG0") is None  # 0 isn't in the alphabet
    assert normalize_code("ABCD-EFGI") is None  # nor I
    assert not set("0O1IL") & set(CODE_ALPHABET)


async def test_issue_stores_only_a_hash_and_formats_the_code(session: AsyncSession) -> None:
    issued = await LinkCodeService(session).issue(guild_id=GUILD, discord_id=7, now=NOW)

    assert len(issued.code) == 9 and issued.code[4] == "-"
    assert issued.expires_at == NOW + timedelta(minutes=15)
    row = (await session.execute(select(LinkCode))).scalars().one()
    assert row.code_hash == hash_code(issued.code.replace("-", ""))
    assert issued.code.replace("-", "") not in row.code_hash


async def test_claim_links_the_discord_account_and_is_single_use(session: AsyncSession) -> None:
    pid = await _player(session)
    service = LinkCodeService(session)
    issued = await service.issue(guild_id=GUILD, discord_id=7, now=NOW)

    outcome = await service.claim(
        guild_id=GUILD, raw_code=issued.code.lower(), brawlhalla_id=10, now=NOW
    )

    assert (outcome.discord_id, outcome.player.id) == (7, pid)
    linked = await LinkService(session, None).get_active_link(  # type: ignore[arg-type]
        guild_id=GUILD, discord_id=7
    )
    assert linked is not None and linked[1].id == pid
    audit = (await session.execute(select(AuditLogEntry))).scalars().one()
    assert (audit.action, audit.source, audit.actor_discord_id) == ("link.claim", "website", 7)
    with pytest.raises(InvalidCodeError):  # reused
        await service.claim(guild_id=GUILD, raw_code=issued.code, brawlhalla_id=10, now=NOW)


async def test_expired_unknown_and_other_guild_codes_are_rejected_alike(
    session: AsyncSession,
) -> None:
    await _player(session)
    service = LinkCodeService(session)
    issued = await service.issue(guild_id=GUILD, discord_id=7, now=NOW)

    for raw, guild, when in (
        (issued.code, GUILD, NOW + timedelta(minutes=15)),  # expired
        ("ABCD-EFGH", GUILD, NOW),  # never issued
        ("nonsense", GUILD, NOW),  # malformed
        (issued.code, 999, NOW),  # another server's code space
    ):
        with pytest.raises(InvalidCodeError) as err:
            await service.claim(guild_id=guild, raw_code=raw, brawlhalla_id=10, now=when)
        assert "invalid or has expired" in str(err.value)


async def test_a_new_code_replaces_the_pending_one(session: AsyncSession) -> None:
    await _player(session)
    service = LinkCodeService(session)
    first = await service.issue(guild_id=GUILD, discord_id=7, now=NOW)
    second = await service.issue(guild_id=GUILD, discord_id=7, now=NOW + timedelta(seconds=5))

    with pytest.raises(InvalidCodeError):
        await service.claim(
            guild_id=GUILD, raw_code=first.code, brawlhalla_id=10, now=NOW + timedelta(seconds=6)
        )
    await service.claim(
        guild_id=GUILD, raw_code=second.code, brawlhalla_id=10, now=NOW + timedelta(seconds=6)
    )


async def test_issuing_is_rate_limited(session: AsyncSession) -> None:
    service = LinkCodeService(session)
    for i in range(5):
        await service.issue(guild_id=GUILD, discord_id=7, now=NOW + timedelta(minutes=i))
    with pytest.raises(RateLimitedError):
        await service.issue(guild_id=GUILD, discord_id=7, now=NOW + timedelta(minutes=6))


async def test_unknown_player_is_not_found(session: AsyncSession) -> None:
    service = LinkCodeService(session)
    issued = await service.issue(guild_id=GUILD, discord_id=7, now=NOW)
    with pytest.raises(NotFoundError):
        await service.claim(guild_id=GUILD, raw_code=issued.code, brawlhalla_id=404, now=NOW)


async def test_no_takeover_of_an_account_someone_else_linked(session: AsyncSession) -> None:
    await _player(session)
    service = LinkCodeService(session)
    owner_code = await service.issue(guild_id=GUILD, discord_id=7, now=NOW)
    await service.claim(guild_id=GUILD, raw_code=owner_code.code, brawlhalla_id=10, now=NOW)

    thief_code = await service.issue(guild_id=GUILD, discord_id=8, now=NOW)
    with pytest.raises(ConflictError):
        await service.claim(guild_id=GUILD, raw_code=thief_code.code, brawlhalla_id=10, now=NOW)


async def test_no_takeover_of_someone_elses_pakistan_board_claim(session: AsyncSession) -> None:
    pid = await _player(session)
    await PakistanBoardRepository(session).add(
        guild_id=GUILD, player_id=pid, added_by_discord_id=7, owner_discord_id=7
    )
    service = LinkCodeService(session)
    code = await service.issue(guild_id=GUILD, discord_id=8, now=NOW)
    with pytest.raises(ConflictError):
        await service.claim(guild_id=GUILD, raw_code=code.code, brawlhalla_id=10, now=NOW)


async def test_claiming_takes_an_unclaimed_board_spot(session: AsyncSession) -> None:
    pid = await _player(session)
    board = PakistanBoardRepository(session)
    await board.add(guild_id=GUILD, player_id=pid, added_by_discord_id=1, owner_discord_id=None)
    service = LinkCodeService(session)
    code = await service.issue(guild_id=GUILD, discord_id=8, now=NOW)

    await service.claim(guild_id=GUILD, raw_code=code.code, brawlhalla_id=10, now=NOW)

    entry = await board.get_active(GUILD, pid)
    assert entry is not None and entry.owner_discord_id == 8


async def test_verification_is_set_and_withdrawn(session: AsyncSession) -> None:
    await _player(session)
    service = LinkCodeService(session)
    code = await service.issue(guild_id=GUILD, discord_id=7, now=NOW)
    await service.claim(guild_id=GUILD, raw_code=code.code, brawlhalla_id=10, now=NOW)
    links = LinkService(session, None)  # type: ignore[arg-type]

    player = await links.set_verified(
        guild_id=GUILD, discord_id=7, staff_discord_id=1, verified=True
    )
    assert player is not None
    from database.repositories.member_player_link_repository import MemberPlayerLinkRepository

    assert await MemberPlayerLinkRepository(session).verified_player_ids() == {player.id}
    # What the Player/Verified role sync mirrors (ADR-109).
    assert await MemberPlayerLinkRepository(session).account_states(GUILD) == {7: True}
    await links.set_verified(guild_id=GUILD, discord_id=7, staff_discord_id=1, verified=False)
    assert await MemberPlayerLinkRepository(session).verified_player_ids() == set()
    assert await MemberPlayerLinkRepository(session).account_states(GUILD) == {7: False}
    assert await MemberPlayerLinkRepository(session).account_states(GUILD + 1) == {}
    assert (
        await links.set_verified(guild_id=GUILD, discord_id=99, staff_discord_id=1, verified=True)
        is None
    )
