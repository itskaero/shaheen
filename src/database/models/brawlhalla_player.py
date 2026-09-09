"""A known Brawlhalla player identity, cached from the Brawlhalla API.

Kept as an internal domain model, separate from the raw API response
models in integrations/brawlhalla/models.py (docs/BRAWLHALLA_API.md's
API-change resilience requirement).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class BrawlhallaPlayer(TimestampMixin, Base):
    __tablename__ = "brawlhalla_players"

    id: Mapped[int] = mapped_column(primary_key=True)
    brawlhalla_player_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    player_name: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str | None] = mapped_column(String(16), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"BrawlhallaPlayer(brawlhalla_player_id={self.brawlhalla_player_id}, "
            f"player_name={self.player_name!r})"
        )
