"""Persistence helpers for permission-related state."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from nonebot_plugin_orm import get_session
from sqlalchemy import select

from apeiria.core.models.ban import BanConsole
from apeiria.core.models.group import GroupConsole
from apeiria.core.models.level import LevelUser
from apeiria.core.models.plugin_info import PluginInfo
from apeiria.domains.exceptions import ResourceNotFoundError


class PermissionStateRepository:
    """Own ORM access for permission, ban, group, and plugin state."""

    async def get_user_level(self, user_id: str, group_id: str) -> int:
        async with get_session() as session:
            result = await session.execute(
                select(LevelUser.level).where(
                    LevelUser.user_id == user_id,
                    LevelUser.group_id == group_id,
                )
            )
            row = result.scalar_one_or_none()
        return row if row is not None else 0

    async def list_user_levels(self) -> list[tuple[str, str, int]]:
        async with get_session() as session:
            result = await session.execute(select(LevelUser))
            rows = result.scalars().all()
        return [(row.user_id, row.group_id, row.level) for row in rows]

    async def set_user_level(self, user_id: str, group_id: str, level: int) -> None:
        async with get_session() as session:
            result = await session.execute(
                select(LevelUser).where(
                    LevelUser.user_id == user_id,
                    LevelUser.group_id == group_id,
                )
            )
            record = result.scalar_one_or_none()
            if record:
                record.level = level
            else:
                session.add(LevelUser(user_id=user_id, group_id=group_id, level=level))
            await session.commit()

    async def list_bans(
        self,
    ) -> list[tuple[int, str | None, str | None, int, str | None]]:
        async with get_session() as session:
            result = await session.execute(select(BanConsole))
            rows = result.scalars().all()
        return [
            (row.id, row.user_id, row.group_id, row.duration, row.reason)
            for row in rows
        ]

    async def list_active_ban_candidates(
        self,
        user_id: str,
        group_id: str | None = None,
    ) -> list[BanConsole]:
        async with get_session() as session:
            stmt = select(BanConsole).where(BanConsole.user_id == user_id)
            if group_id:
                stmt = stmt.where(
                    (BanConsole.group_id == group_id) | (BanConsole.group_id.is_(None))
                )
            result = await session.execute(stmt)
            bans = result.scalars().all()
        return list(bans)

    async def create_ban(
        self,
        *,
        user_id: str,
        group_id: str | None,
        duration: int,
        reason: str | None,
    ) -> tuple[int, str | None, str | None, int, str | None]:
        async with get_session() as session:
            record = BanConsole(
                user_id=user_id,
                group_id=group_id,
                ban_time=datetime.now(timezone.utc),
                duration=duration,
                reason=reason,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)

        return (
            record.id,
            record.user_id,
            record.group_id,
            record.duration,
            record.reason,
        )

    async def delete_ban(self, ban_id: int) -> tuple[str | None, str | None]:
        async with get_session() as session:
            result = await session.execute(
                select(BanConsole).where(BanConsole.id == ban_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise ResourceNotFoundError

            user_id = record.user_id
            group_id = record.group_id
            await session.delete(record)
            await session.commit()

        return user_id, group_id

    async def get_group_disabled_plugins(self, group_id: str) -> list[str]:
        async with get_session() as session:
            result = await session.execute(
                select(GroupConsole.disabled_plugins).where(
                    GroupConsole.group_id == group_id
                )
            )
            raw = result.scalar_one_or_none()
        try:
            disabled = json.loads(raw) if raw else []
        except (json.JSONDecodeError, TypeError):
            disabled = []
        return [module for module in disabled if isinstance(module, str)]

    async def get_group_bot_status(self, group_id: str) -> bool:
        async with get_session() as session:
            result = await session.execute(
                select(GroupConsole.bot_status).where(GroupConsole.group_id == group_id)
            )
            bot_status = result.scalar_one_or_none()
        return bot_status is not False

    async def get_plugin_global_enabled(self, plugin_module: str) -> bool:
        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo.is_global_enabled).where(
                    PluginInfo.module_name == plugin_module
                )
            )
            enabled = result.scalar_one_or_none()
        return True if enabled is None else bool(enabled)


permission_state_repository = PermissionStateRepository()
