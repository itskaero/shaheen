"""Declarative base and shared mixins for all ORM models."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


def str_enum_column(enum_cls: type[enum.Enum], length: int) -> SAEnum:
    """A non-native Enum column that persists `.value`, not `.name`.

    SQLAlchemy's Enum type persists a Python Enum's `.name` by default,
    which is surprising for a StrEnum whose members are named differently
    from their values (e.g. `PENDING_CONFIRMATION = "pending_confirmation"`).
    `length` must be at least as long as the longest *value*.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [e.value for e in cls],
    )


class Base(DeclarativeBase):
    """Shared declarative base for all Shaheen models."""


class TimestampMixin:
    """Adds timezone-aware created_at/updated_at columns.

    docs/DATABASE.md requires timestamps to be timezone-aware.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
