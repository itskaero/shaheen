"""Links a ShaheenMember to a BrawlhallaPlayer, with history.

Rows are never deleted on unlink — `unlinked_at` is set instead, so a
member's linking history is preserved (docs/DATABASE.md).  At most one row
per member may have `unlinked_at IS NULL` (the active link); enforced by a
partial unique index rather than application code alone.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin

_ACTIVE_LINK_ONLY = text("unlinked_at IS NULL")


class MemberPlayerLink(TimestampMixin, Base):
    __tablename__ = "member_player_links"
    __table_args__ = (
        Index(
            "uq_one_active_link_per_member",
            "shaheen_member_id",
            unique=True,
            postgresql_where=_ACTIVE_LINK_ONLY,
            sqlite_where=_ACTIVE_LINK_ONLY,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shaheen_member_id: Mapped[int] = mapped_column(
        ForeignKey("shaheen_members.id"), nullable=False, index=True
    )
    brawlhalla_player_id: Mapped[int] = mapped_column(
        ForeignKey("brawlhalla_players.id"), nullable=False, index=True
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"MemberPlayerLink(shaheen_member_id={self.shaheen_member_id}, "
            f"brawlhalla_player_id={self.brawlhalla_player_id}, "
            f"active={self.unlinked_at is None})"
        )
