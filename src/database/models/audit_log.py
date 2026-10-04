"""Append-only audit trail for account and moderation actions
(docs/DECISIONS.md ADR-107): link claims, verification changes, and later
reports. `actor_discord_id` is who did it (None for an anonymous website
visitor); `subject` names what it was done to, in plain text.
"""

from __future__ import annotations

from sqlalchemy import JSON, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class AuditLogEntry(TimestampMixin, Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # "discord" | "website"
    actor_discord_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
