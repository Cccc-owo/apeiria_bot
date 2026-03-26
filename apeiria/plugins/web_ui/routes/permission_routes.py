"""Permission routes — users, levels, bans."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from apeiria.core.i18n import t
from apeiria.domains.exceptions import ResourceNotFoundError
from apeiria.domains.permissions import permission_service
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import (
    BanCreateRequest,
    BanItem,
    UpdateLevelRequest,
    UserLevelItem,
)

router = APIRouter()


@router.get("/users", response_model=list[UserLevelItem])
async def list_users(_: Annotated[Any, Depends(require_auth)]) -> list[UserLevelItem]:
    rows = await permission_service.list_user_levels()
    return [
        UserLevelItem(user_id=user_id, group_id=group_id, level=level)
        for r in rows
        for user_id, group_id, level in [r]
    ]


@router.patch("/users/{user_id}")
async def update_user_level(
    user_id: str,
    body: UpdateLevelRequest,
    _: Annotated[Any, Depends(require_auth)],
    group_id: str = "",
) -> dict[str, str]:
    if not group_id:
        raise HTTPException(
            status_code=400,
            detail=t("web_ui.permissions.group_id_required"),
        )

    await permission_service.set_user_level(user_id, group_id, body.level)
    return {"status": "ok"}


@router.get("/bans", response_model=list[BanItem])
async def list_bans(_: Annotated[Any, Depends(require_auth)]) -> list[BanItem]:
    rows = await permission_service.list_bans()
    return [
        BanItem(
            id=ban_id,
            user_id=user_id,
            group_id=group_id,
            duration=duration,
            reason=reason,
        )
        for ban_id, user_id, group_id, duration, reason in rows
    ]


@router.post("/bans", response_model=BanItem)
async def create_ban(
    body: BanCreateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> BanItem:
    ban_id, user_id, group_id, duration, reason = await permission_service.create_ban(
        user_id=body.user_id,
        group_id=body.group_id,
        duration=body.duration,
        reason=body.reason,
    )
    return BanItem(
        id=ban_id,
        user_id=user_id,
        group_id=group_id,
        duration=duration,
        reason=reason,
    )


@router.delete("/bans/{ban_id}")
async def delete_ban(
    ban_id: int,
    _: Annotated[Any, Depends(require_auth)],
) -> dict[str, str]:
    try:
        await permission_service.delete_ban(ban_id)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.permissions.ban_not_found"),
        ) from None
    return {"status": "ok"}
