"""Dashboard domain services."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import nonebot

from apeiria.core.utils.webui_build import (
    read_frontend_build_status,
    web_dir,
    write_frontend_build_meta,
)


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


@dataclass(frozen=True)
class WebUIBuildStatusSnapshot:
    """Web UI frontend build status for dashboard actions."""

    is_built: bool
    is_stale: bool
    can_build: bool
    build_tool: str | None
    detail: str | None


@dataclass(frozen=True)
class WebUIBuildRunSnapshot:
    """Web UI frontend rebuild result."""

    is_built: bool
    is_stale: bool
    can_build: bool
    build_tool: str | None
    detail: str | None
    logs: str


@dataclass(frozen=True)
class WebUIBuildStreamEvent:
    """Stream event emitted while rebuilding frontend assets."""

    event: str
    chunk: str = ""
    detail: str | None = None
    status: WebUIBuildStatusSnapshot | None = None


class DashboardService:
    """Provide dashboard data and runtime restart orchestration."""

    def __init__(self) -> None:
        self._start_time = time.time()
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._restart_task: asyncio.Task[None] | None = None
        self._project_root = Path(__file__).resolve().parent.parent.parent.parent
        self._web_dir = web_dir(self._project_root)

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

    def get_web_ui_build_status(self) -> WebUIBuildStatusSnapshot:
        """Return whether frontend assets match the current source fingerprint."""
        build_tool = shutil.which("pnpm") or shutil.which("npm")
        can_build = build_tool is not None and (self._web_dir / "package.json").is_file()
        status = read_frontend_build_status(self._project_root)
        return WebUIBuildStatusSnapshot(
            is_built=status.is_built,
            is_stale=status.is_stale,
            can_build=can_build,
            build_tool=Path(build_tool).name if build_tool else None,
            detail=status.detail,
        )

    async def rebuild_web_ui(self) -> WebUIBuildRunSnapshot:
        """Build frontend assets in the local web workspace."""
        status = self.get_web_ui_build_status()
        if not status.can_build:
            raise RuntimeError("build_tool_unavailable")

        command = ["pnpm", "build"] if status.build_tool == "pnpm" else ["npm", "run", "build"]
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._web_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        logs = self._merge_build_logs(
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
        if process.returncode != 0:
            raise RuntimeError(logs.strip() or "build_failed")
        write_frontend_build_meta(self._project_root)
        next_status = self.get_web_ui_build_status()
        return WebUIBuildRunSnapshot(
            is_built=next_status.is_built,
            is_stale=next_status.is_stale,
            can_build=next_status.can_build,
            build_tool=next_status.build_tool,
            detail=next_status.detail,
            logs=logs,
        )

    async def stream_web_ui_rebuild(self) -> AsyncIterator[bytes]:
        """Stream frontend build logs as newline-delimited JSON."""
        status = self.get_web_ui_build_status()
        if not status.can_build:
            raise RuntimeError("build_tool_unavailable")

        command = ["pnpm", "build"] if status.build_tool == "pnpm" else ["npm", "run", "build"]
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._web_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_chunks: list[str] = []
        assert process.stdout is not None
        while True:
            chunk = await process.stdout.read(1024)
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            output_chunks.append(text)
            yield self._encode_build_stream_event(
                WebUIBuildStreamEvent(event="chunk", chunk=text)
            )

        return_code = await process.wait()
        logs = "".join(output_chunks).strip()
        if return_code != 0:
            detail = logs or "build_failed"
            yield self._encode_build_stream_event(
                WebUIBuildStreamEvent(event="error", detail=detail)
            )
            return

        write_frontend_build_meta(self._project_root)
        next_status = self.get_web_ui_build_status()
        yield self._encode_build_stream_event(
            WebUIBuildStreamEvent(event="done", status=next_status)
        )

    def _merge_build_logs(self, stdout: str, stderr: str) -> str:
        sections: list[str] = []
        if stdout.strip():
            sections.append(stdout.strip())
        if stderr.strip():
            sections.append(stderr.strip())
        return "\n\n".join(sections)

    def _encode_build_stream_event(self, event: WebUIBuildStreamEvent) -> bytes:
        payload: dict[str, object] = {"event": event.event}
        if event.chunk:
            payload["chunk"] = event.chunk
        if event.detail is not None:
            payload["detail"] = event.detail
        if event.status is not None:
            payload["status"] = {
                "is_built": event.status.is_built,
                "is_stale": event.status.is_stale,
                "can_build": event.status.can_build,
                "build_tool": event.status.build_tool,
                "detail": event.status.detail,
            }
        return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")

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
