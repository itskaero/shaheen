"""A report about a player, from Discord's /report or the website's Report
Player (docs/DECISIONS.md ADR-111). One moderation record shared by both
sources; staff review it in #report.

A reported player is named by whatever the reporter could point at: a
Discord member, a Brawlhalla account, or just a name. The reporter is never
shown publicly; `reporter_discord_id` is None for a website visitor.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin

REPORT_STATUSES = ("open", "resolved", "dismissed")


class PlayerReport(TimestampMixin, Base):
    __tablename__ = "player_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # "discord" | "website"
    reporter_discord_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    reported_discord_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reported_brawlhalla_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reported_name: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    # The #report embed, once posted; None until then.
    report_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
