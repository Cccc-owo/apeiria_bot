"""Plugin routes — list and manage plugins."""

from __future__ import annotations

from typing import Annotated, Any

import nonebot
from fastapi import APIRouter, Depends, HTTPException

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import (
    get_plugin_extra,
    get_plugin_name,
    get_plugin_protection_reason,
    get_plugin_source,
)
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import PluginItem

router = APIRouter()


@router.get("/", response_model=list[PluginItem])
async def list_plugins(_: Annotated[Any, Depends(require_auth)]) -> list[PluginItem]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.plugin_info import PluginInfo

    enabled_map: dict[str, bool] = {}
    async with get_session() as session:
        result = await session.execute(
            select(PluginInfo.module_name, PluginInfo.is_global_enabled)
        )
        enabled_map = dict(result.all())

    result: list[PluginItem] = []
    for plugin in nonebot.get_loaded_plugins():
        meta = plugin.metadata
        extra = get_plugin_extra(plugin)
        protected_reason = get_plugin_protection_reason(plugin.module_name)
        result.append(
            PluginItem(
                module_name=plugin.module_name,
                name=get_plugin_name(plugin),
                description=meta.description if meta else None,
                source=get_plugin_source(plugin),
                plugin_type=extra.plugin_type.value if extra else "normal",
                admin_level=extra.admin_level if extra else 0,
                is_global_enabled=enabled_map.get(plugin.module_name, True),
                version=extra.version if extra else None,
                is_protected=protected_reason is not None,
                protected_reason=protected_reason,
            )
        )
    return result


@router.patch("/{module_name}")
async def update_plugin(
    module_name: str,
    _: Annotated[Any, Depends(require_auth)],
    *,
    enabled: bool = True,
) -> dict[str, str]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.plugin_info import PluginInfo
    from apeiria.core.services.cache import get_cache
    from apeiria.core.utils.helpers import get_plugin_protection_reason

    async with get_session() as session:
        result = await session.execute(
            select(PluginInfo).where(PluginInfo.module_name == module_name)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail=t("web_ui.plugins.not_found"))
        if not enabled:
            reason = get_plugin_protection_reason(module_name)
            if reason:
                raise HTTPException(
                    status_code=400,
                    detail=t("web_ui.plugins.protected", reason=reason),
                )
        record.is_global_enabled = enabled
        await session.commit()

    await get_cache().delete(f"plugin_global:{module_name}")
    return {"status": "ok"}
