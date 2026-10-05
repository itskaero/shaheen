"""Player reports (docs/DECISIONS.md ADR-111): the rules shared by Discord's
/report and the website's Report Player, so both create the same moderation
record. No Discord here — the bot posts the #report embed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import RateLimitedError, ShaheenError
from database.models.player_report import PlayerReport
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.player_report_repository import PlayerReportRepository

MIN_REASON = 10
MAX_REASON = 1000
MAX_NAME = 64
# Per reporter, so one person can't flood #report.
REPORT_LIMIT = 3
REPORT_WINDOW = timedelta(minutes=10)


def clean_text(value: str, *, limit: int) -> str:
    """Collapse whitespace and drop control characters; never trust input."""
    printable = "".join(ch if ch.isprintable() else " " for ch in value)
    return " ".join(printable.split())[:limit]


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._reports = PlayerReportRepository(session)
        self._audit = AuditLogRepository(session)

    async def create(
        self,
        *,
        guild_id: int,
        source: str,
        reported_name: str,
        reason: str,
        reporter_discord_id: int | None = None,
        reported_discord_id: int | None = None,
        reported_brawlhalla_id: int | None = None,
        now: datetime | None = None,
    ) -> PlayerReport:
        now = now or datetime.now(UTC)
        name = clean_text(reported_name, limit=MAX_NAME)
        text = clean_text(reason, limit=MAX_REASON)
        if not name:
            raise ShaheenError("Say who you're reporting.")
        if len(text) < MIN_REASON:
            raise ShaheenError(
                f"Give a reason of at least {MIN_REASON} characters so staff can act on it."
            )
        if reporter_discord_id is not None:
            if reporter_discord_id == reported_discord_id:
                raise ShaheenError("You can't report yourself.")
            recent = await self._reports.count_by_reporter_since(
                guild_id, reporter_discord_id, now - REPORT_WINDOW
            )
            if recent >= REPORT_LIMIT:
                raise RateLimitedError(
                    "You've sent several reports just now — staff will review them. "
                    "Try again in a few minutes."
                )

        report = await self._reports.add(
            PlayerReport(
                guild_id=guild_id,
                source=source,
                reporter_discord_id=reporter_discord_id,
                reported_discord_id=reported_discord_id,
                reported_brawlhalla_id=reported_brawlhalla_id,
                reported_name=name,
                reason=text,
                status="open",
            )
        )
        await self._audit.add(
            guild_id=guild_id,
            action="report.create",
            source=source,
            actor_discord_id=reporter_discord_id,
            subject=f"report #{report.id}: {name}",
        )
        return report

    async def mark_posted(self, report: PlayerReport, message_id: int) -> None:
        report.report_message_id = message_id

    async def unposted(self, guild_id: int) -> list[PlayerReport]:
        return await self._reports.list_unposted(guild_id)
