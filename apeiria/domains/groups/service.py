"""Group domain services."""

from __future__ import annotations

import json
from dataclasses import dataclass

from apeiria.core.utils.helpers import get_plugin_protection_reason, safe_json_loads
from apeiria.domains.exceptions import ProtectedPluginError, ResourceNotFoundError
from apeiria.domains.permissions import permission_service


@dataclass(frozen=True)
class GroupRecord:
    """Normalized group record for interfaces."""

    group_id: str
    group_name: str | None
    bot_status: bool
    disabled_plugins: list[str]


class GroupService:
    """Manage persisted per-group settings."""

    async def list_groups(self) -> list[GroupRecord]:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.group import GroupConsole

        async with get_session() as session:
            result = await session.execute(select(GroupConsole))
            rows = result.scalars().all()
        return [self._to_record(row) for row in rows]

    async def get_group(self, group_id: str) -> GroupRecord:
        row = await self._fetch_group(group_id)
        return self._to_record(row)

    async def update_group_status(
        self,
        group_id: str,
        *,
        enabled: bool | None,
    ) -> None:
        row = await self._fetch_group(group_id)
        if enabled is not None:
            row.bot_status = enabled

        from nonebot_plugin_orm import get_session

        async with get_session() as session:
            session.add(row)
            await session.commit()
        await permission_service.invalidate_group_bot_status_cache(group_id)

    async def update_group_disabled_plugins(
        self,
        group_id: str,
        disabled_plugins: list[str],
    ) -> None:
        protected = [
            f"{module} ({reason})"
            for module in disabled_plugins
            if (reason := get_plugin_protection_reason(module))
        ]
        if protected:
            raise ProtectedPluginError(", ".join(protected))

        row = await self._fetch_group(group_id)
        row.disabled_plugins = json.dumps(sorted(set(disabled_plugins)))

        from nonebot_plugin_orm import get_session

        async with get_session() as session:
            session.add(row)
            await session.commit()
        await permission_service.invalidate_group_plugin_cache(group_id)

    async def toggle_group_plugin(
        self,
        group_id: str,
        plugin_module: str,
        *,
        enable: bool,
    ) -> None:
        row = await self._fetch_group(group_id, create_if_missing=True)
        disabled = safe_json_loads(row.disabled_plugins, default=[])
        normalized = [module for module in disabled if isinstance(module, str)]

        if enable:
            normalized = [module for module in normalized if module != plugin_module]
        elif plugin_module not in normalized:
            normalized.append(plugin_module)

        await self.update_group_disabled_plugins(group_id, normalized)

    async def _fetch_group(self, group_id: str, *, create_if_missing: bool = False):
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.group import GroupConsole

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

    def _to_record(self, row: object) -> GroupRecord:
        raw_disabled = getattr(row, "disabled_plugins", "[]")
        disabled_plugins = [
            module
            for module in safe_json_loads(raw_disabled, default=[])
            if isinstance(module, str)
            if not get_plugin_protection_reason(module)
        ]
        return GroupRecord(
            group_id=row.group_id,
            group_name=row.group_name,
            bot_status=row.bot_status,
            disabled_plugins=disabled_plugins,
        )


group_service = GroupService()
