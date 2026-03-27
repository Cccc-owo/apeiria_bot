"""Persistence helpers for plugin catalog state."""

from __future__ import annotations

from nonebot_plugin_orm import get_session
from sqlalchemy import select

from apeiria.core.models.plugin_info import PluginInfo
from apeiria.domains.exceptions import ResourceNotFoundError


class PluginCatalogRepository:
    """Own ORM access for plugin catalog persistence."""

    async def get_enabled_map(self) -> dict[str, bool]:
        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo.module_name, PluginInfo.is_global_enabled)
            )
            rows = result.all()
        return {row[0]: row[1] for row in rows}

    async def set_plugin_enabled(self, module_name: str, *, enabled: bool) -> None:
        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo).where(PluginInfo.module_name == module_name)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise ResourceNotFoundError(module_name)
            record.is_global_enabled = enabled
            await session.commit()


plugin_catalog_repository = PluginCatalogRepository()
