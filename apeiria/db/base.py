"""Base declarative class and shared mixins for Apeiria ORM models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now_iso() -> str:
    """Return the current UTC time as an ISO-formatted string."""
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    """Base class that all Apeiria ORM model tables inherit from."""


class ISOTimestampMixin:
    """Mixin that adds ISO-formatted ``created_at`` and ``updated_at`` columns."""

    created_at: Mapped[str] = mapped_column(String, default=_now_iso, nullable=False)
    updated_at: Mapped[str] = mapped_column(
        String, default=_now_iso, onupdate=_now_iso, nullable=False
    )
