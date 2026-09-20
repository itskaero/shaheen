"""Membership application rules (docs/DECISIONS.md ADR-089).

Discord-agnostic per docs/ARCHITECTURE.md: plain ids and strings in,
Application rows out. The cog and views own every Discord effect — posting
the review card, editing roles, sending the DM — so the rules that actually
matter (one open application at a time, a cooldown after a denial, a
decision can only be made once) are testable without a gateway and reusable
by the future website.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ShaheenError
from database.models.application import Application, ApplicationStatus
from database.repositories.application_repository import ApplicationRepository

# How long someone must wait after a denial before applying again. Long
# enough that "apply again immediately" isn't a way to wear staff down,
# short enough that someone who fixed the reason they were denied isn't
# locked out for a season.
REAPPLY_COOLDOWN_DAYS = 14

MAX_NOTE_LENGTH = 512


@dataclass(frozen=True)
class ApplicationAnswers:
    """One submitted form. Free-text fields are the applicant's own words.

    Whatever a reviewer sees here is untrusted user input: the embed builder
    truncates it and Discord renders it as plain text, never as a command.
    """

    brawlhalla_identifier: str
    region: str
    current_rank: str
    motivation: str
    referred_by: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "brawlhalla_identifier": self.brawlhalla_identifier,
            "region": self.region,
            "current_rank": self.current_rank,
            "motivation": self.motivation,
            "referred_by": self.referred_by,
        }


class ApplicationService:
    def __init__(self, session: AsyncSession) -> None:
        self._applications = ApplicationRepository(session)

    async def submit(
        self,
        *,
        guild_id: int,
        discord_id: int,
        answers: ApplicationAnswers,
        now: datetime | None = None,
    ) -> Application:
        """File a new application.

        Raises ShaheenError when one is already open, or when the member was
        denied inside the cooldown window.
        """
        moment = now or datetime.now(UTC)

        if await self._applications.get_pending(guild_id=guild_id, discord_id=discord_id):
            raise ShaheenError(
                "You already have an application under review — staff will get to it."
            )

        latest = await self._applications.get_latest(guild_id=guild_id, discord_id=discord_id)
        if latest is not None and latest.status is ApplicationStatus.DENIED:
            remaining = _cooldown_remaining(latest.reviewed_at, moment)
            if remaining is not None:
                raise ShaheenError(
                    f"Your last application was declined. You can apply again in "
                    f"{remaining} day(s)."
                )
        if latest is not None and latest.status is ApplicationStatus.APPROVED:
            raise ShaheenError("You've already been approved — you're in.")

        attempt = await self._applications.count_for_member(
            guild_id=guild_id, discord_id=discord_id
        )
        return await self._applications.add(
            Application(
                guild_id=guild_id,
                discord_id=discord_id,
                status=ApplicationStatus.PENDING,
                answers=answers.as_dict(),
                brawlhalla_identifier=answers.brawlhalla_identifier,
                attempt=attempt + 1,
            )
        )

    async def attach_review_message(self, application: Application, message_id: int) -> None:
        application.review_message_id = message_id

    async def decide(
        self,
        application: Application,
        *,
        approved: bool,
        reviewer_discord_id: int,
        note: str | None = None,
        now: datetime | None = None,
    ) -> Application:
        """Approve or deny, exactly once.

        The guard matters more than it looks: the Approve/Deny buttons live
        on a message that stays in the channel forever, so two staff members
        clicking at the same time — or anyone clicking an old card — must
        not re-decide a settled application.
        """
        if application.status is not ApplicationStatus.PENDING:
            raise ShaheenError(
                f"That application was already {application.status.value} — nothing to do."
            )
        if reviewer_discord_id == application.discord_id:
            raise ShaheenError("You can't review your own application.")

        application.status = ApplicationStatus.APPROVED if approved else ApplicationStatus.DENIED
        application.reviewer_discord_id = reviewer_discord_id
        application.review_note = (note or None) and note[:MAX_NOTE_LENGTH]
        application.reviewed_at = now or datetime.now(UTC)
        return application

    async def withdraw(self, *, guild_id: int, discord_id: int) -> Application:
        """An applicant pulling their own pending application."""
        pending = await self._applications.get_pending(guild_id=guild_id, discord_id=discord_id)
        if pending is None:
            raise NotFoundError("You don't have an application under review.")
        pending.status = ApplicationStatus.WITHDRAWN
        pending.reviewed_at = datetime.now(UTC)
        return pending

    async def pending(self, guild_id: int, *, limit: int = 25) -> list[Application]:
        return await self._applications.list_pending(guild_id, limit=limit)

    async def for_review_message(self, message_id: int) -> Application | None:
        return await self._applications.get_by_review_message(message_id)

    async def latest_for(self, *, guild_id: int, discord_id: int) -> Application | None:
        return await self._applications.get_latest(guild_id=guild_id, discord_id=discord_id)


def _cooldown_remaining(reviewed_at: datetime | None, now: datetime) -> int | None:
    """Whole days left on the re-apply cooldown, or None once it has passed.

    A denial with no timestamp (older row, or a manual DB edit) is treated
    as expired rather than locking the applicant out forever.
    """
    if reviewed_at is None:
        return None
    if reviewed_at.tzinfo is None:
        reviewed_at = reviewed_at.replace(tzinfo=UTC)
    unlocks_at = reviewed_at + timedelta(days=REAPPLY_COOLDOWN_DAYS)
    if now >= unlocks_at:
        return None
    return max(1, (unlocks_at - now).days + 1)
