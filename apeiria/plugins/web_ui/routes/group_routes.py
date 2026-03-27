"""Group routes — list and manage groups."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from apeiria.core.i18n import t
from apeiria.domains.exceptions import ProtectedPluginError, ResourceNotFoundError
from apeiria.domains.groups import group_service
from apeiria.plugins.web_ui.auth import require_control_panel
from apeiria.plugins.web_ui.models import GroupItem

router = APIRouter()


def _to_group_item(r: Any) -> GroupItem:
    return GroupItem(
        group_id=r.group_id,
        group_name=r.group_name,
        bot_status=r.bot_status,
        disabled_plugins=list(r.disabled_plugins),
    )


@router.get("/", response_model=list[GroupItem])
async def list_groups(
    _: Annotated[Any, Depends(require_control_panel)],
) -> list[GroupItem]:
    rows = await group_service.list_groups()
    return [_to_group_item(r) for r in rows]


@router.get("/{group_id}", response_model=GroupItem)
async def get_group(
    group_id: str, _: Annotated[Any, Depends(require_control_panel)]
) -> GroupItem:
    try:
        r = await group_service.get_group(group_id)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.groups.not_found"),
        ) from None
    return _to_group_item(r)


@router.patch("/{group_id}")
async def update_group(
    group_id: str,
    _: Annotated[Any, Depends(require_control_panel)],
    *,
    bot_status: bool | None = None,
) -> dict[str, str]:
    try:
        await group_service.update_group_status(group_id, enabled=bot_status)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.groups.not_found"),
        ) from None
    return {"status": "ok"}


@router.patch("/{group_id}/plugins")
async def update_group_plugins(
    group_id: str,
    disabled_plugins: list[str],
    _: Annotated[Any, Depends(require_control_panel)],
) -> dict[str, str]:
    try:
        await group_service.update_group_disabled_plugins(group_id, disabled_plugins)
    except ProtectedPluginError as exc:
        raise HTTPException(
            status_code=400,
            detail=t("web_ui.groups.protected_plugins", plugins=str(exc)),
        ) from None
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.groups.not_found"),
        ) from None
    return {"status": "ok"}
