"""One-time codes that link a Discord account to a player profile on the
website (docs/DECISIONS.md ADR-107).

`/link` with no arguments issues one; the website's "Claim this profile"
form redeems it. Only a SHA-256 of the code is stored, so a database
leak can't be replayed. Codes are single use and expire.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class LinkCode(TimestampMixin, Base):
    __tablename__ = "link_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_for_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("brawlhalla_players.id"), nullable=True
    )
