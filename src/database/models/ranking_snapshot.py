"""An append-only point-in-time ranked snapshot for a Brawlhalla player.

Never overwritten — docs/DATABASE.md's History section requires snapshots
to be append-oriented so rating/progression history can be reconstructed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class RankingSnapshot(TimestampMixin, Base):
    __tablename__ = "ranking_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    brawlhalla_player_id: Mapped[int] = mapped_column(
        ForeignKey("brawlhalla_players.id"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    region: Mapped[str | None] = mapped_column(String(16), nullable=True)
    global_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"RankingSnapshot(brawlhalla_player_id={self.brawlhalla_player_id}, "
            f"captured_at={self.captured_at}, tier={self.tier!r})"
        )
