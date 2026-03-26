"""Group routes — list and manage groups."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import is_plugin_protected, safe_json_loads
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import GroupItem

router = APIRouter()


def _to_group_item(r: Any) -> GroupItem:
    disabled_plugins = safe_json_loads(r.disabled_plugins, default=[])
    return GroupItem(
        group_id=r.group_id,
        group_name=r.group_name,
        bot_status=r.bot_status,
        disabled_plugins=[
            module
            for module in disabled_plugins
            if isinstance(module, str)
            if not is_plugin_protected(module)
        ],
    )


@router.get("/", response_model=list[GroupItem])
async def list_groups(_: Annotated[Any, Depends(require_auth)]) -> list[GroupItem]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole

    async with get_session() as session:
        result = await session.execute(select(GroupConsole))
        rows = result.scalars().all()
    return [_to_group_item(r) for r in rows]


@router.get("/{group_id}", response_model=GroupItem)
async def get_group(
    group_id: str, _: Annotated[Any, Depends(require_auth)]
) -> GroupItem:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole

    async with get_session() as session:
        result = await session.execute(
            select(GroupConsole).where(GroupConsole.group_id == group_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail=t("web_ui.groups.not_found"))
    return _to_group_item(r)


@router.patch("/{group_id}")
async def update_group(
    group_id: str,
    _: Annotated[Any, Depends(require_auth)],
    *,
    bot_status: bool | None = None,
) -> dict[str, str]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole
    from apeiria.core.utils.permission import invalidate_group_bot_status_cache

    async with get_session() as session:
        result = await session.execute(
            select(GroupConsole).where(GroupConsole.group_id == group_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail=t("web_ui.groups.not_found"))
        if bot_status is not None:
            record.bot_status = bot_status
        await session.commit()
    await invalidate_group_bot_status_cache(group_id)
    return {"status": "ok"}


@router.patch("/{group_id}/plugins")
async def update_group_plugins(
    group_id: str,
    disabled_plugins: list[str],
    _: Annotated[Any, Depends(require_auth)],
) -> dict[str, str]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole
    from apeiria.core.utils.helpers import get_plugin_protection_reason
    from apeiria.core.utils.permission import invalidate_group_plugin_cache

    protected = [
        f"{module} ({reason})"
        for module in disabled_plugins
        if (reason := get_plugin_protection_reason(module))
    ]
    if protected:
        raise HTTPException(
            status_code=400,
            detail=t("web_ui.groups.protected_plugins", plugins=", ".join(protected)),
        )

    async with get_session() as session:
        result = await session.execute(
            select(GroupConsole).where(GroupConsole.group_id == group_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail=t("web_ui.groups.not_found"))
        record.disabled_plugins = json.dumps(disabled_plugins)
        await session.commit()

    await invalidate_group_plugin_cache(group_id)
    return {"status": "ok"}
