"""A clan scrim announcement (docs/COMMANDS.md `/scrim`), filled via signups."""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin, str_enum_column
from database.models.match import MatchKind, MatchSide


class ScrimStatus(enum.StrEnum):
    OPEN = "open"
    FULL = "full"
    CANCELLED = "cancelled"


class Scrim(TimestampMixin, Base):
    __tablename__ = "scrims"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_by_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False
    )
    kind: Mapped[MatchKind] = mapped_column(str_enum_column(MatchKind, length=8))
    status: Mapped[ScrimStatus] = mapped_column(
        str_enum_column(ScrimStatus, length=16), default=ScrimStatus.OPEN
    )
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    announcement_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    announcement_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Scrim(id={self.id}, kind={self.kind}, status={self.status})"


class ScrimSignup(Base):
    __tablename__ = "scrim_signups"
    __table_args__ = (UniqueConstraint("scrim_id", "shaheen_member_id", name="uq_scrim_signup"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scrim_id: Mapped[int] = mapped_column(ForeignKey("scrims.id"), nullable=False, index=True)
    shaheen_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False, index=True
    )
    side: Mapped[MatchSide] = mapped_column(str_enum_column(MatchSide, length=1))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ScrimSignup(scrim_id={self.scrim_id}, side={self.side})"
