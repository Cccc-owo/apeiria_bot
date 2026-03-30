"""Background tasks for plugin store operations."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from apeiria.cli_store import (
    install_plugin_package,
    install_plugin_requirement_with_auto_module,
    update_plugin_package,
)
from apeiria.package_ids import normalize_package_id

from .models import PluginStoreInstallRequest, PluginStoreTask, StorePluginItem
from .service import plugin_store_service


def _format_task_error(exc: Exception) -> str:
    """Return a trimmed multi-line error string for task logs and API payloads."""
    message = str(exc).strip()
    return message or exc.__class__.__name__


class PluginStoreTaskService:
    """Own in-memory plugin store tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, PluginStoreTask] = {}
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._active_install_keys: set[tuple[str, ...]] = set()

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

    async def create_plugin_update_task(
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
        self._validate_update_request(item, request)
        install_key = ("update", *self._install_key(request))
        if install_key in self._active_install_keys:
            msg = "update task already running for this plugin"
            raise ValueError(msg)

        task_id = uuid4().hex
        task = PluginStoreTask(
            task_id=task_id,
            title=f"Update {item.name}",
            status="pending",
            logs="",
            created_at=_now(),
        )
        self._tasks[task_id] = task
        self._active_install_keys.add(install_key)
        background_task = asyncio.create_task(
            self._run_plugin_update_task(task_id, item, request, install_key)
        )
        self._background_tasks.add(background_task)
        background_task.add_done_callback(self._background_tasks.discard)
        return task

    async def create_manual_plugin_install_task(
        self,
        requirement: str,
        module_name: str | None = None,
    ) -> PluginStoreTask:
        target = requirement.strip()
        resolved_module = (module_name or "").strip()
        if not target:
            msg = "package name is required"
            raise ValueError(msg)

        install_key = ("manual", target, resolved_module or "auto")
        if install_key in self._active_install_keys:
            msg = "install task already running for this target"
            raise ValueError(msg)

        task_id = uuid4().hex
        task = PluginStoreTask(
            task_id=task_id,
            title=f"Install {target}",
            status="pending",
            logs="",
            created_at=_now(),
        )
        self._tasks[task_id] = task
        self._active_install_keys.add(install_key)
        background_task = asyncio.create_task(
            self._run_manual_plugin_install_task(
                task_id,
                target,
                resolved_module,
                install_key,
            )
        )
        self._background_tasks.add(background_task)
        background_task.add_done_callback(self._background_tasks.discard)
        return task

    async def create_manual_plugin_update_task(
        self,
        requirement: str,
        module_name: str,
    ) -> PluginStoreTask:
        target = requirement.strip()
        resolved_module = module_name.strip()
        if not target:
            msg = "package name is required"
            raise ValueError(msg)
        if not resolved_module:
            msg = "plugin module name is required"
            raise ValueError(msg)

        install_key = ("manual-update", target, resolved_module)
        if install_key in self._active_install_keys:
            msg = "update task already running for this target"
            raise ValueError(msg)

        task_id = uuid4().hex
        task = PluginStoreTask(
            task_id=task_id,
            title=f"Update {resolved_module}",
            status="pending",
            logs="",
            created_at=_now(),
        )
        self._tasks[task_id] = task
        self._active_install_keys.add(install_key)
        background_task = asyncio.create_task(
            self._run_manual_plugin_update_task(
                task_id,
                target,
                resolved_module,
                install_key,
            )
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
                logs=(f"{self._tasks[task_id].logs}install succeeded\n"),
            )
        except Exception as exc:  # noqa: BLE001
            error = _format_task_error(exc)
            self._update_task(
                task_id,
                status="failed",
                finished_at=_now(),
                error=error,
                logs=(f"{self._tasks[task_id].logs}install failed\n{error}\n"),
            )
        finally:
            self._active_install_keys.discard(install_key)

    async def _run_manual_plugin_install_task(
        self,
        task_id: str,
        requirement: str,
        module_name: str,
        install_key: tuple[str, ...],
    ) -> None:
        self._update_task(
            task_id,
            status="running",
            started_at=_now(),
            logs=(
                "source: manual\n"
                f"requirement: {requirement}\n"
                f"module: {module_name or 'auto'}\n"
            ),
        )
        try:
            if module_name:
                result = await asyncio.to_thread(
                    install_plugin_package,
                    requirement,
                    module_name,
                )
            else:
                result = await asyncio.to_thread(
                    install_plugin_requirement_with_auto_module,
                    requirement,
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
                logs=(f"{self._tasks[task_id].logs}install succeeded\n"),
            )
        except Exception as exc:  # noqa: BLE001
            error = _format_task_error(exc)
            self._update_task(
                task_id,
                status="failed",
                finished_at=_now(),
                error=error,
                logs=(f"{self._tasks[task_id].logs}install failed\n{error}\n"),
            )
        finally:
            self._active_install_keys.discard(install_key)

    async def _run_manual_plugin_update_task(
        self,
        task_id: str,
        requirement: str,
        module_name: str,
        install_key: tuple[str, ...],
    ) -> None:
        self._update_task(
            task_id,
            status="running",
            started_at=_now(),
            logs=(
                "source: installed\n"
                f"requirement: {requirement}\n"
                f"module: {module_name}\n"
            ),
        )
        try:
            result = await asyncio.to_thread(
                update_plugin_package,
                requirement,
                module_name,
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
                logs=(f"{self._tasks[task_id].logs}update succeeded\n"),
            )
        except Exception as exc:  # noqa: BLE001
            error = _format_task_error(exc)
            self._update_task(
                task_id,
                status="failed",
                finished_at=_now(),
                error=error,
                logs=(f"{self._tasks[task_id].logs}update failed\n{error}\n"),
            )
        finally:
            self._active_install_keys.discard(install_key)

    async def _run_plugin_update_task(
        self,
        task_id: str,
        item: StorePluginItem,
        request: PluginStoreInstallRequest,
        install_key: tuple[str, ...],
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
                update_plugin_package,
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
                logs=(f"{self._tasks[task_id].logs}update succeeded\n"),
            )
        except Exception as exc:  # noqa: BLE001
            error = _format_task_error(exc)
            self._update_task(
                task_id,
                status="failed",
                finished_at=_now(),
                error=error,
                logs=(f"{self._tasks[task_id].logs}update failed\n{error}\n"),
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

    def _validate_update_request(
        self,
        item: StorePluginItem,
        request: PluginStoreInstallRequest,
    ) -> None:
        self._validate_install_request(item, request)
        if not item.can_update:
            msg = "plugin cannot be updated from store"
            raise ValueError(msg)
        installed_package = normalize_package_id(item.installed_package or "")
        store_package = normalize_package_id(request.package_name)
        if not installed_package or installed_package != store_package:
            msg = "installed package does not match store package"
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
