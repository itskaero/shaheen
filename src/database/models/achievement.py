"""The Achievement catalog — reference data, seeded by the Phase 3 migration.

The catalog's source of truth is services/achievements.py; the migration
seeds these rows from it (docs/DECISIONS.md ADR-030).
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class Achievement(TimestampMixin, Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Achievement(key={self.key!r}, name={self.name!r})"
