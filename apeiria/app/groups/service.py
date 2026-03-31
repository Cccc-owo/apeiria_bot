"""Group application services."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from apeiria.app.groups.repository import group_repository
from apeiria.shared.exceptions import ProtectedPluginError
from apeiria.shared.json_utils import safe_json_loads
from apeiria.shared.plugin_introspection import get_plugin_protection_reason

if TYPE_CHECKING:
    from apeiria.infra.db.models.group import GroupConsole


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
        rows = await group_repository.list_groups()
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

        await group_repository.save_group(row)

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

        await group_repository.save_group(row)

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

    async def _fetch_group(
        self,
        group_id: str,
        *,
        create_if_missing: bool = False,
    ) -> "GroupConsole":
        return await group_repository.get_group(
            group_id,
            create_if_missing=create_if_missing,
        )

    def _to_record(self, row: "GroupConsole") -> GroupRecord:
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
