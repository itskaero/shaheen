"""Single-elimination tournament tables (docs/DECISIONS.md ADR-035).

TournamentEntrant is a solo player (1v1) or a pre-formed duo (2v2) —
TournamentEntrantMember is the join table for the latter. TournamentMatch
is one bracket slot; its `match_id` is set once both entrants are known
and the slot becomes reportable.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin, str_enum_column
from database.models.match import MatchKind


class TournamentStatus(enum.StrEnum):
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TournamentMatchStatus(enum.StrEnum):
    PENDING = "pending"  # one or both entrants not decided yet (waiting on a prior round)
    READY = "ready"  # both entrants known, no Match created/reported yet
    AWAITING_REPORT = "awaiting_report"  # Match created, waiting on /report + confirmation
    COMPLETED = "completed"
    BYE = "bye"  # only one entrant was assigned; they advance automatically


class Tournament(TimestampMixin, Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    kind: Mapped[MatchKind] = mapped_column(str_enum_column(MatchKind, length=8))
    status: Mapped[TournamentStatus] = mapped_column(
        str_enum_column(TournamentStatus, length=16), default=TournamentStatus.REGISTRATION
    )
    created_by_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Tournament(id={self.id}, name={self.name!r}, status={self.status})"


class TournamentEntrant(Base):
    __tablename__ = "tournament_entrants"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id"), nullable=False, index=True
    )
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eliminated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"TournamentEntrant(id={self.id}, seed={self.seed})"


class TournamentEntrantMember(Base):
    __tablename__ = "tournament_entrant_members"
    __table_args__ = (
        UniqueConstraint("tournament_entrant_id", "shaheen_member_id", name="uq_entrant_member"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_entrant_id: Mapped[int] = mapped_column(
        ForeignKey("tournament_entrants.id"), nullable=False, index=True
    )
    shaheen_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False, index=True
    )


class TournamentMatch(Base):
    __tablename__ = "tournament_matches"
    __table_args__ = (
        UniqueConstraint(
            "tournament_id", "round_number", "slot_index", name="uq_tournament_bracket_slot"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id"), nullable=False, index=True
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    entrant_a_id: Mapped[int | None] = mapped_column(
        ForeignKey("tournament_entrants.id"), nullable=True
    )
    entrant_b_id: Mapped[int | None] = mapped_column(
        ForeignKey("tournament_entrants.id"), nullable=True
    )
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    winner_entrant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tournament_entrants.id"), nullable=True
    )
    status: Mapped[TournamentMatchStatus] = mapped_column(
        str_enum_column(TournamentMatchStatus, length=16),
        default=TournamentMatchStatus.PENDING,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"TournamentMatch(tournament_id={self.tournament_id}, "
            f"round={self.round_number}, slot={self.slot_index}, status={self.status})"
        )
