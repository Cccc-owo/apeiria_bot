"""Permission routes — users, levels, bans."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from apeiria.core.i18n import t
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
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.level import LevelUser

    async with get_session() as session:
        result = await session.execute(select(LevelUser))
        rows = result.scalars().all()
    return [
        UserLevelItem(user_id=r.user_id, group_id=r.group_id, level=r.level)
        for r in rows
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

    from apeiria.core.utils.permission import set_user_level

    await set_user_level(user_id, group_id, body.level)
    return {"status": "ok"}


@router.get("/bans", response_model=list[BanItem])
async def list_bans(_: Annotated[Any, Depends(require_auth)]) -> list[BanItem]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.ban import BanConsole

    async with get_session() as session:
        result = await session.execute(select(BanConsole))
        rows = result.scalars().all()
    return [
        BanItem(
            id=r.id,
            user_id=r.user_id,
            group_id=r.group_id,
            duration=r.duration,
            reason=r.reason,
        )
        for r in rows
    ]


@router.post("/bans", response_model=BanItem)
async def create_ban(
    body: BanCreateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> BanItem:
    from nonebot_plugin_orm import get_session

    from apeiria.core.models.ban import BanConsole
    from apeiria.core.services.cache import get_cache

    async with get_session() as session:
        record = BanConsole(
            user_id=body.user_id,
            group_id=body.group_id,
            ban_time=datetime.now(timezone.utc),
            duration=body.duration,
            reason=body.reason,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

    await get_cache().delete(f"ban:{body.user_id}")
    return BanItem(
        id=record.id,
        user_id=record.user_id,
        group_id=record.group_id,
        duration=record.duration,
        reason=record.reason,
    )


@router.delete("/bans/{ban_id}")
async def delete_ban(
    ban_id: int,
    _: Annotated[Any, Depends(require_auth)],
) -> dict[str, str]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.ban import BanConsole
    from apeiria.core.services.cache import get_cache

    async with get_session() as session:
        result = await session.execute(
            select(BanConsole).where(BanConsole.id == ban_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=404,
                detail=t("web_ui.permissions.ban_not_found"),
            )
        user_id = record.user_id
        await session.delete(record)
        await session.commit()

    if user_id:
        await get_cache().delete(f"ban:{user_id}")
    return {"status": "ok"}
