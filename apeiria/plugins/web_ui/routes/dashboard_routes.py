"""Dashboard routes — bot status overview."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Annotated, Any

import nonebot
from fastapi import APIRouter, Depends

from apeiria.core.i18n import t
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import OperationStatusResponse, StatusResponse

router = APIRouter()

_start_time = time.time()
_background_tasks: set[asyncio.Task[None]] = set()


async def _restart_process() -> None:
    await asyncio.sleep(0.5)
    argv = sys.argv[:] if sys.argv else ["bot.py"]
    os.execv(sys.executable, [sys.executable, *argv])


@router.get("/status", response_model=StatusResponse)
async def get_status(_: Annotated[Any, Depends(require_auth)]) -> StatusResponse:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import func, select

    from apeiria.core.models.ban import BanConsole
    from apeiria.core.models.group import GroupConsole
    from apeiria.core.models.plugin_info import PluginInfo

    adapters = list(nonebot.get_adapters().keys())
    plugins = nonebot.get_loaded_plugins()

    async with get_session() as session:
        disabled_plugins_count = (
            await session.scalar(
                select(func.count())
                .select_from(PluginInfo)
                .where(PluginInfo.is_global_enabled.is_(False))
            )
            or 0
        )
        groups_count = (
            await session.scalar(select(func.count()).select_from(GroupConsole)) or 0
        )
        disabled_groups_count = (
            await session.scalar(
                select(func.count())
                .select_from(GroupConsole)
                .where(GroupConsole.bot_status.is_(False))
            )
            or 0
        )
        bans_count = (
            await session.scalar(select(func.count()).select_from(BanConsole)) or 0
        )

    return StatusResponse(
        status="running",
        uptime=time.time() - _start_time,
        plugins_count=len(plugins),
        disabled_plugins_count=disabled_plugins_count,
        groups_count=groups_count,
        disabled_groups_count=disabled_groups_count,
        bans_count=bans_count,
        adapters=adapters,
    )


@router.post("/restart", response_model=OperationStatusResponse)
async def restart_bot(
    _: Annotated[Any, Depends(require_auth)],
) -> OperationStatusResponse:
    task = asyncio.create_task(_restart_process())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return OperationStatusResponse(detail=t("web_ui.dashboard.restart_scheduled"))
