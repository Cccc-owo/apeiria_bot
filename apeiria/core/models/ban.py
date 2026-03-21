"""BanConsole model — ban records for users and groups."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from nonebot_plugin_orm import Model
from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class BanConsole(Model):
    """Ban records. user_id=None means group-level ban."""

    __tablename__ = "ban_console"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    group_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ban_level: Mapped[int] = mapped_column(default=0)
    ban_time: Mapped[datetime] = mapped_column(insert_default=func.now())
    duration: Mapped[int] = mapped_column(default=0)  # Seconds, 0 = permanent
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
