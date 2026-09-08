"""An append-only point-in-time per-Legend snapshot for a Brawlhalla player.

One row per played Legend per snapshot cycle — docs/DECISIONS.md ADR-029.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class LegendSnapshot(TimestampMixin, Base):
    __tablename__ = "legend_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    brawlhalla_player_id: Mapped[int] = mapped_column(
        ForeignKey("brawlhalla_players.id"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    legend_id: Mapped[int] = mapped_column(Integer, nullable=False)
    legend_name_key: Mapped[str] = mapped_column(String(32), nullable=False)
    games: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    damagedealt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    falls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"LegendSnapshot(brawlhalla_player_id={self.brawlhalla_player_id}, "
            f"legend_name_key={self.legend_name_key!r}, captured_at={self.captured_at})"
        )
