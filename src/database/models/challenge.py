"""A 1v1 challenge between two members (docs/COMMANDS.md `/challenge <user>`)."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin, str_enum_column


class ChallengeStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class Challenge(TimestampMixin, Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    challenger_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False
    )
    opponent_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False
    )
    status: Mapped[ChallengeStatus] = mapped_column(
        str_enum_column(ChallengeStatus, length=16), default=ChallengeStatus.PENDING
    )
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Challenge(id={self.id}, status={self.status})"
