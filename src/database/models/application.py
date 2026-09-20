"""A membership application and its review (docs/DECISIONS.md ADR-089).

Before this, joining Shaheen was: land in the server, get the auto-assigned
Guest role, and hope a staff member ran /verify on you. There was no way to
apply, no record of who asked, no queue, and no audit trail of who decided
what or why. This is that record.

Answers are stored as JSON rather than one column per question so the form
can change without a migration — the questions are presentation, the
decision is the data.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Enum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class ApplicationStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        # The queue reads "pending, oldest first" and the submit path asks
        # "does this member already have one open".
        Index("ix_applications_guild_status", "guild_id", "status"),
        Index("ix_applications_guild_discord", "guild_id", "discord_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # The applicant's raw Discord id. Deliberately not a ShaheenMember FK:
    # an applicant is not a member yet, and forcing a member row at submit
    # time would put people in the roster before anyone approved them.
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.PENDING,
    )
    answers: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    # The review card posted to #applications. Stored so the Approve/Deny
    # buttons can find their application from the message they are attached
    # to, which keeps their custom_ids static and therefore restart-safe
    # (bot/views/application.py).
    review_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    reviewer_discord_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Which Brawlhalla-facing identifier the applicant gave, kept out of
    # `answers` because /apply validates it and the reviewer reads it first.
    brawlhalla_identifier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Denormalised so the queue can show "3rd application" without a join.
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Application(id={self.id}, discord_id={self.discord_id}, status={self.status.value!r})"
        )
