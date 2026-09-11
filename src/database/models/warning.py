"""A moderation warning issued to a Discord member.

Deliberately keyed by raw `discord_id`/`guild_id`, not FK'd through
`DiscordUser`/`ShaheenMember` — a member can be warned without ever having
run `/link`, and shouldn't need to (docs/DECISIONS.md ADR-065).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class Warning(TimestampMixin, Base):
    __tablename__ = "warnings"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    moderator_discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    # /clearwarnings soft-clears (sets False) rather than deleting rows, so
    # the moderation history survives being cleared — an audit trail, not
    # just a live count.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Warning(guild_id={self.guild_id}, discord_id={self.discord_id})"
