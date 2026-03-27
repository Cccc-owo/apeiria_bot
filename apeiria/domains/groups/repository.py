"""Persistence helpers for group settings."""

from __future__ import annotations

from nonebot_plugin_orm import get_session
from sqlalchemy import select

from apeiria.core.models.group import GroupConsole
from apeiria.domains.exceptions import ResourceNotFoundError


class GroupRepository:
    """Own ORM access for persisted group settings."""

    async def list_groups(self) -> list[GroupConsole]:
        async with get_session() as session:
            result = await session.execute(select(GroupConsole))
            rows = result.scalars().all()
        return list(rows)

    async def get_group(
        self,
        group_id: str,
        *,
        create_if_missing: bool = False,
    ) -> GroupConsole:
        async with get_session() as session:
            result = await session.execute(
                select(GroupConsole).where(GroupConsole.group_id == group_id)
            )
            row = result.scalar_one_or_none()
            if row is None and create_if_missing:
                row = GroupConsole(group_id=group_id, disabled_plugins="[]")
                session.add(row)
                await session.commit()
                await session.refresh(row)
            if row is None:
                raise ResourceNotFoundError(group_id)
        return row

    async def save_group(self, row: GroupConsole) -> None:
        async with get_session() as session:
            session.add(row)
            await session.commit()


group_repository = GroupRepository()
