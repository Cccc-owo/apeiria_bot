"""Persistence helpers for plugin catalog state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nonebot_plugin_orm import get_session
from sqlalchemy import select

from apeiria.core.configs.models import PluginExtraData
from apeiria.core.models.plugin_info import PluginInfo
from apeiria.domains.exceptions import ResourceNotFoundError

if TYPE_CHECKING:
    from nonebot.plugin import Plugin


class PluginCatalogRepository:
    """Own ORM access for plugin catalog persistence."""

    async def get_enabled_map(self) -> dict[str, bool]:
        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo.module_name, PluginInfo.is_global_enabled)
            )
            rows = result.all()
        return {row[0]: row[1] for row in rows}

    async def get_plugin_info_map(self) -> dict[str, PluginInfo]:
        """Return persisted plugin info indexed by module name."""
        async with get_session() as session:
            result = await session.execute(select(PluginInfo))
            rows = result.scalars().all()
        return {row.module_name: row for row in rows}

    async def set_plugin_enabled(self, module_name: str, *, enabled: bool) -> bool:
        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo).where(PluginInfo.module_name == module_name)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise ResourceNotFoundError(module_name)
            changed = record.is_global_enabled != enabled
            if not changed:
                return False
            record.is_global_enabled = enabled
            await session.commit()
        return True

    async def ensure_plugin_record_by_module_name(self, module_name: str) -> None:
        """Ensure a minimal plugin record exists for unloaded-but-managed plugins."""
        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo).where(PluginInfo.module_name == module_name)
            )
            record = result.scalar_one_or_none()
            if record is not None:
                return

            session.add(
                PluginInfo(
                    module_name=module_name,
                    name=module_name,
                )
            )
            await session.commit()

    async def ensure_plugin_record(self, plugin: Plugin) -> None:
        meta = plugin.metadata
        extra: PluginExtraData | None = None
        if meta and meta.extra:
            extra = PluginExtraData.from_extra(meta.extra)

        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo).where(PluginInfo.module_name == plugin.module_name)
            )
            record = result.scalar_one_or_none()
            if record is None:
                session.add(
                    PluginInfo(
                        module_name=plugin.module_name,
                        name=meta.name if meta else plugin.name,
                        description=meta.description if meta else None,
                        usage=meta.usage if meta else None,
                        plugin_type=extra.plugin_type.value if extra else "normal",
                        admin_level=extra.admin_level if extra else 0,
                        author=extra.author if extra else None,
                        version=extra.version if extra else None,
                    )
                )
                await session.commit()
                return

            record.name = meta.name if meta else plugin.name
            record.description = meta.description if meta else None
            record.usage = meta.usage if meta else None
            record.plugin_type = extra.plugin_type.value if extra else "normal"
            record.admin_level = extra.admin_level if extra else 0
            record.author = extra.author if extra else None
            record.version = extra.version if extra else None
            await session.commit()


plugin_catalog_repository = PluginCatalogRepository()
