"""SQLAlchemy ORM model for access control rules."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from apeiria.db.base import Base


class AccessRule(Base):
    """SQLAlchemy ORM model for a single access control rule.

    A rule associates a subject with an action, optionally scoped to a specific
    plugin, and carries a priority used to order rules in the permission chain.
    """

    __tablename__ = "access_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_type: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[str] = mapped_column(String, nullable=False)
    plugin_name: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
