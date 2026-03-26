"""Plugin domain services."""

from __future__ import annotations

from dataclasses import dataclass

import nonebot

from apeiria.core.utils.helpers import (
    get_plugin_extra,
    get_plugin_dependents,
    get_plugin_name,
    get_plugin_protection_reason,
    get_plugin_required_plugins,
    get_plugin_source,
)
from apeiria.domains.exceptions import ProtectedPluginError, ResourceNotFoundError
from apeiria.domains.permissions import permission_service


@dataclass(frozen=True)
class PluginCatalogItem:
    """Normalized plugin list entry."""

    module_name: str
    name: str
    description: str | None
    source: str
    is_global_enabled: bool
    is_protected: bool
    protected_reason: str | None
    plugin_type: str
    admin_level: int
    author: str | None
    version: str | None
    required_plugins: list[str]
    dependent_plugins: list[str]


class PluginCatalogService:
    """List and mutate plugin registry state."""

    async def list_plugins(self) -> list[PluginCatalogItem]:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.plugin_info import PluginInfo

        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo.module_name, PluginInfo.is_global_enabled)
            )
            enabled_map = {row[0]: row[1] for row in result.all()}

        items: list[PluginCatalogItem] = []
        for plugin in nonebot.get_loaded_plugins():
            meta = plugin.metadata
            extra = get_plugin_extra(plugin)
            protected_reason = get_plugin_protection_reason(plugin.module_name)
            items.append(
                PluginCatalogItem(
                    module_name=plugin.module_name,
                    name=get_plugin_name(plugin),
                    description=meta.description if meta else None,
                    source=get_plugin_source(plugin),
                    is_global_enabled=enabled_map.get(plugin.module_name, True),
                    is_protected=protected_reason is not None,
                    protected_reason=protected_reason,
                    plugin_type=extra.plugin_type.value if extra else "normal",
                    admin_level=extra.admin_level if extra else 0,
                    author=extra.author if extra else None,
                    version=extra.version if extra else None,
                    required_plugins=get_plugin_required_plugins(plugin),
                    dependent_plugins=get_plugin_dependents(plugin.module_name),
                )
            )
        return items

    async def set_plugin_enabled(self, module_name: str, *, enabled: bool) -> None:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.plugin_info import PluginInfo

        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo).where(PluginInfo.module_name == module_name)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise ResourceNotFoundError(module_name)

            if not enabled:
                reason = get_plugin_protection_reason(module_name)
                if reason:
                    raise ProtectedPluginError(reason)

            record.is_global_enabled = enabled
            await session.commit()

        await permission_service.invalidate_plugin_global_cache(module_name)


plugin_catalog_service = PluginCatalogService()
