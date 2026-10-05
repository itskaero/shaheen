"""Player reports (docs/DECISIONS.md ADR-111): validation, rate limiting,
audit, and the unposted queue the bot drains into #report."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import RateLimitedError, ShaheenError
from database.models.audit_log import AuditLogEntry
from services.report_service import REPORT_LIMIT, ReportService, clean_text

GUILD = 1


async def _report(service: ReportService, **overrides: object) -> object:
    args: dict[str, object] = {
        "guild_id": GUILD,
        "source": "discord",
        "reporter_discord_id": 7,
        "reported_discord_id": 8,
        "reported_name": "Cheater",
        "reason": "Teaming in ranked and spamming slurs",
    }
    args.update(overrides)
    return await service.create(**args)  # type: ignore[arg-type]


async def test_a_report_is_stored_audited_and_queued(session: AsyncSession) -> None:
    service = ReportService(session)
    report = await _report(service)
    assert report.status == "open"  # type: ignore[attr-defined]
    assert [r.id for r in await service.unposted(GUILD)] == [report.id]  # type: ignore[attr-defined]
    await service.mark_posted(report, 555)  # type: ignore[arg-type]
    assert await service.unposted(GUILD) == []
    audit = (await session.execute(select(AuditLogEntry))).scalars().all()
    assert [a.action for a in audit] == ["report.create"]


@pytest.mark.parametrize("reason", ["", "too short", "   \n\t  "])
async def test_a_reason_needs_substance(session: AsyncSession, reason: str) -> None:
    with pytest.raises(ShaheenError):
        await _report(ReportService(session), reason=reason)


async def test_nobody_reports_themselves(session: AsyncSession) -> None:
    with pytest.raises(ShaheenError):
        await _report(ReportService(session), reported_discord_id=7)


async def test_a_reporter_is_rate_limited(session: AsyncSession) -> None:
    service = ReportService(session)
    for _ in range(REPORT_LIMIT):
        await _report(service)
    with pytest.raises(RateLimitedError):
        await _report(service)
    # ...but a website visitor (no Discord id) and other reporters aren't.
    await _report(service, reporter_discord_id=None, source="website")
    await _report(service, reporter_discord_id=9)


async def test_old_reports_dont_count_towards_the_limit(session: AsyncSession) -> None:
    service = ReportService(session)
    for _ in range(REPORT_LIMIT):
        await _report(service)
    # The window is measured from created_at, which the DB stamps "now";
    # a reporter checking far in the future is clear again.
    await _report(service, now=datetime.now(UTC) + timedelta(hours=1))


def test_text_is_cleaned() -> None:
    assert clean_text("  bad\x00 name\n\nhere  ", limit=64) == "bad name here"
    assert clean_text("x" * 100, limit=10) == "x" * 10
