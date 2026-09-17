"""An append-only point-in-time snapshot of Discord guild-level stats.

Deliberately guild-wide numbers only (member count, boost tier/count) —
never anything tied to an individual member's Discord identity. See
docs/DECISIONS.md ADR-040 (public identity is Brawlhalla identity, never
Discord identity) and the ADR for this round, which reaffirms rather than
reverses that boundary. Append-only like RankingSnapshot, for the same
reason: so a future trend view doesn't require redesigning the table.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class GuildSnapshot(TimestampMixin, Base):
    __tablename__ = "guild_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    member_count: Mapped[int] = mapped_column(Integer, nullable=False)
    boost_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    boost_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"GuildSnapshot(guild_id={self.guild_id}, captured_at={self.captured_at}, "
            f"member_count={self.member_count})"
        )
