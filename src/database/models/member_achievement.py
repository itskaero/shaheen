"""An achievement awarded to a member. Unique per (member, achievement)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class MemberAchievement(TimestampMixin, Base):
    __tablename__ = "member_achievements"
    __table_args__ = (
        UniqueConstraint("shaheen_member_id", "achievement_id", name="uq_member_achievement"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shaheen_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False, index=True
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id"), nullable=False, index=True
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"MemberAchievement(shaheen_member_id={self.shaheen_member_id}, "
            f"achievement_id={self.achievement_id})"
        )
