"""Dashboard domain services."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass

import nonebot


@dataclass(frozen=True)
class DashboardStatusSnapshot:
    """Status snapshot used by dashboard interfaces."""

    status: str
    uptime: float
    plugins_count: int
    disabled_plugins_count: int
    groups_count: int
    disabled_groups_count: int
    bans_count: int
    adapters: list[str]


@dataclass(frozen=True)
class DashboardEventSnapshot:
    """Recent high-signal event shown on the dashboard."""

    timestamp: str
    level: str
    source: str
    message: str


class DashboardService:
    """Provide dashboard data and runtime restart orchestration."""

    def __init__(self) -> None:
        self._start_time = time.time()
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._restart_task: asyncio.Task[None] | None = None

    async def get_status_snapshot(self) -> DashboardStatusSnapshot:
        """Collect the current dashboard metrics snapshot."""
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
                await session.scalar(
                    select(func.count()).select_from(GroupConsole)
                )
                or 0
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

        return DashboardStatusSnapshot(
            status="running",
            uptime=time.time() - self._start_time,
            plugins_count=len(plugins),
            disabled_plugins_count=disabled_plugins_count,
            groups_count=groups_count,
            disabled_groups_count=disabled_groups_count,
            bans_count=bans_count,
            adapters=adapters,
        )

    def get_recent_events(
        self,
        *,
        limit: int = 8,
    ) -> list[DashboardEventSnapshot]:
        """Return the most recent warning/error events for the dashboard."""
        from apeiria.core.services.log import log_buffer

        high_signal_levels = {"WARNING", "ERROR", "CRITICAL"}
        entries = [
            DashboardEventSnapshot(
                timestamp=entry.timestamp,
                level=entry.level,
                source=entry.source,
                message=entry.message,
            )
            for entry in log_buffer.get_recent(100)
            if entry.level in high_signal_levels
        ]
        return entries[-limit:][::-1]

    def schedule_restart(self) -> None:
        if self._restart_task is None or self._restart_task.done():
            self._restart_task = asyncio.create_task(self._restart_process())
            self._background_tasks.add(self._restart_task)
            self._restart_task.add_done_callback(self._background_tasks.discard)

    async def _restart_process(self) -> None:
        await asyncio.sleep(0.5)
        argv = sys.argv[:] if sys.argv else ["bot.py"]
        os.execv(sys.executable, [sys.executable, *argv])


dashboard_service = DashboardService()
