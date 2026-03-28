"""Background tasks for plugin store operations."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from apeiria.cli_store import install_plugin_package

from .models import PluginStoreInstallRequest, PluginStoreTask, StorePluginItem
from .service import plugin_store_service


class PluginStoreTaskService:
    """Own in-memory plugin store tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, PluginStoreTask] = {}
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._active_install_keys: set[tuple[str, str, str, str]] = set()

    def get_task(self, task_id: str) -> PluginStoreTask | None:
        return self._tasks.get(task_id)

    async def create_plugin_install_task(
        self,
        request: PluginStoreInstallRequest,
    ) -> PluginStoreTask:
        item = await plugin_store_service.get_item(
            source_id=request.source_id,
            plugin_id=request.plugin_id,
            item_type=request.type,
        )
        if item is None:
            msg = "store plugin not found"
            raise ValueError(msg)
        self._validate_install_request(item, request)
        install_key = self._install_key(request)
        if install_key in self._active_install_keys:
            msg = "install task already running for this plugin"
            raise ValueError(msg)

        task_id = uuid4().hex
        task = PluginStoreTask(
            task_id=task_id,
            title=f"Install {item.name}",
            status="pending",
            logs="",
            created_at=_now(),
        )
        self._tasks[task_id] = task
        self._active_install_keys.add(install_key)
        background_task = asyncio.create_task(
            self._run_plugin_install_task(task_id, item, request, install_key)
        )
        self._background_tasks.add(background_task)
        background_task.add_done_callback(self._background_tasks.discard)
        return task

    async def _run_plugin_install_task(
        self,
        task_id: str,
        item: StorePluginItem,
        request: PluginStoreInstallRequest,
        install_key: tuple[str, str, str, str],
    ) -> None:
        self._update_task(
            task_id,
            status="running",
            started_at=_now(),
            logs=(
                f"source: {item.source_name}\n"
                f"plugin: {item.name}\n"
                f"package: {request.package_name}\n"
                f"module: {request.module_name}\n"
            ),
        )
        try:
            result = await asyncio.to_thread(
                install_plugin_package,
                request.package_name,
                request.module_name,
            )
            self._update_task(
                task_id,
                status="succeeded",
                finished_at=_now(),
                result={
                    "requirement": result.requirement,
                    "module_name": result.module_name,
                    "restart_required": True,
                },
                logs=(
                    f"{self._tasks[task_id].logs}"
                    "install succeeded\n"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            self._update_task(
                task_id,
                status="failed",
                finished_at=_now(),
                error=str(exc),
                logs=(
                    f"{self._tasks[task_id].logs}"
                    f"install failed: {exc}\n"
                ),
            )
        finally:
            self._active_install_keys.discard(install_key)

    def _validate_install_request(
        self,
        item: StorePluginItem,
        request: PluginStoreInstallRequest,
    ) -> None:
        if item.package_name != request.package_name:
            msg = "package name mismatch"
            raise ValueError(msg)
        if item.module_name != request.module_name:
            msg = "module name mismatch"
            raise ValueError(msg)

    def _update_task(self, task_id: str, **updates: object) -> None:
        current = self._tasks[task_id]
        self._tasks[task_id] = replace(current, **updates)

    def _install_key(
        self,
        request: PluginStoreInstallRequest,
    ) -> tuple[str, str, str, str]:
        return (
            request.source_id,
            request.plugin_id,
            request.package_name,
            request.module_name,
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()


plugin_store_task_service = PluginStoreTaskService()
