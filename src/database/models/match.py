"""A clan match record — internal win/loss tracking, distinct from live
Brawlhalla ranked data (docs/DATABASE.md's `Match`, deferred from earlier
phases until Phase 4).

Origin-agnostic: Challenge/Scrim/TournamentMatch each hold their own
`match_id` pointing here, rather than Match tracking where it came from.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin, str_enum_column


class MatchKind(enum.StrEnum):
    ONE_V_ONE = "1v1"
    TWO_V_TWO = "2v2"


class MatchStatus(enum.StrEnum):
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class MatchSide(enum.StrEnum):
    A = "A"
    B = "B"


class Match(TimestampMixin, Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    kind: Mapped[MatchKind] = mapped_column(str_enum_column(MatchKind, length=8))
    status: Mapped[MatchStatus] = mapped_column(
        str_enum_column(MatchStatus, length=24),
        default=MatchStatus.PENDING_CONFIRMATION,
    )
    reported_by_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=True
    )
    reported_winning_side: Mapped[MatchSide | None] = mapped_column(
        str_enum_column(MatchSide, length=1), nullable=True
    )
    winning_side: Mapped[MatchSide | None] = mapped_column(
        str_enum_column(MatchSide, length=1), nullable=True
    )
    resolved_by_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Match(id={self.id}, kind={self.kind}, status={self.status})"


class MatchParticipant(Base):
    __tablename__ = "match_participants"
    __table_args__ = (
        UniqueConstraint("match_id", "shaheen_member_id", name="uq_match_participant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    shaheen_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False, index=True
    )
    side: Mapped[MatchSide] = mapped_column(str_enum_column(MatchSide, length=1))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"MatchParticipant(match_id={self.match_id}, side={self.side})"
