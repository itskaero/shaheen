"""A Discord user's membership record within one Shaheen guild.

`guild_id` is carried explicitly rather than assumed (docs/DECISIONS.md
ADR-011), even though Shaheen operates a single guild today.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin
from database.models.discord_user import DiscordUser


class ShaheenMember(TimestampMixin, Base):
    __tablename__ = "shaheen_members"
    __table_args__ = (UniqueConstraint("discord_user_id", "guild_id", name="uq_member_per_guild"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_user_id: Mapped[int] = mapped_column(
        ForeignKey("discord_users.id"), nullable=False, index=True
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    discord_user: Mapped[DiscordUser] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ShaheenMember(discord_user_id={self.discord_user_id}, guild_id={self.guild_id})"
