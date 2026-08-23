"""SQLAlchemy ORM model for key/value application settings."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from apeiria.db.base import Base


class ApeiriaSetting(Base):
    """SQLAlchemy ORM model for a single key/value application setting.

    Each row stores a setting as a string key paired with its value, used to
    hold key/value configuration such as Web authentication details.
    """

    __tablename__ = "apeiria_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
