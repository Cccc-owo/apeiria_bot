from __future__ import annotations

import asyncio
import shutil
import uuid
from typing import Any

from nonebot.log import logger

_TASK_CLEANUP_DELAY = 60.0


class TaskRunner:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._tasks: set[asyncio.Task[Any]] = set()

    async def start(  # noqa: PLR0913
        self,
        kind: str,
        name: str,
        pkg_requirement: str = "",
        *,
        module_name: str | None = None,
        uninstall: bool = False,
        keep_config: bool = False,
        update: bool = False,
    ) -> str:
        task_id = uuid.uuid4().hex
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues[task_id] = queue
        if update:
            coro = self._do_update(queue, kind, name, pkg_requirement)
        elif uninstall:
            coro = self._do_uninstall(queue, kind, name, keep_config=keep_config)
        else:
            coro = self._do_install(queue, kind, name, pkg_requirement, module_name)
        task = asyncio.create_task(self._run_task(queue, coro))
        self._tasks.add(task)

        def _on_task_done(done_task: asyncio.Task[Any]) -> None:
            self._tasks.discard(done_task)
            done_task.get_loop().call_later(
                _TASK_CLEANUP_DELAY, self._queues.pop, task_id, None
            )

        task.add_done_callback(_on_task_done)
        return task_id

    async def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]] | None:
        return self._queues.get(task_id)

    async def _run_task(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        coro: Any,
    ) -> None:
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Background task failed")
            await queue.put({"type": "error", "ok": False, "message": str(exc)})

    async def _run_subprocess(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        uv: str,
        *args: str,
    ) -> int | None:
        proc = await asyncio.create_subprocess_exec(
            uv,
            *args,
            "--directory",
            ".apeiria",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        if proc.stdout is None:
            return None
        async for line in proc.stdout:
            text = line.decode("utf-8", errors="replace").rstrip()
            await self._emit(queue, "output", text)
        await proc.wait()
        return proc.returncode

    async def _require_uv(self, queue: asyncio.Queue[dict[str, Any]]) -> str | None:
        uv = shutil.which("uv")
        if uv is None:
            await queue.put({"type": "error", "ok": False, "message": "uv not found"})
        return uv

    @staticmethod
    def _read_manifest(kind: str) -> dict:
        if kind == "plugin":
            from apeiria.plugin.manager import _read_plugins_yaml

            return _read_plugins_yaml()
        from apeiria.plugin.adapter_manager import _read_adapters_yaml

        return _read_adapters_yaml()

    @staticmethod
    def _write_manifest(kind: str, data: dict) -> None:
        if kind == "plugin":
            from apeiria.plugin.manager import _write_plugins_yaml

            _write_plugins_yaml(data)
            return
        from apeiria.plugin.adapter_manager import _write_adapters_yaml

        _write_adapters_yaml(data)

    @staticmethod
    def _remove_config(kind: str, name: str) -> None:
        if kind == "plugin":
            from apeiria.plugin.manager import _remove_plugin_config

            _remove_plugin_config(name)
            return
        from apeiria.plugin.adapter_manager import _remove_adapter_config

        _remove_adapter_config(name)

    @staticmethod
    def _toml_add_adapter(name: str, module_name: str | None) -> None:
        from apeiria.plugin.adapter_manager import _toml_add_adapter

        _toml_add_adapter(name, module_name or name)

    @staticmethod
    def _toml_remove_adapter(name: str) -> None:
        from apeiria.plugin.adapter_manager import _toml_remove_adapter

        _toml_remove_adapter(name)

    async def _sync_manifest_env(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        from apeiria.env.sync import sync_apeiria_env

        await self._emit(queue, "output", "> uv sync")
        sync_apeiria_env()

    async def _do_install(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        kind: str,
        name: str,
        pkg_requirement: str,
        module_name: str | None,
    ) -> None:
        uv = await self._require_uv(queue)
        if uv is None:
            return

        await self._emit(queue, "output", f"> uv add {pkg_requirement}")
        rc = await self._run_subprocess(queue, uv, "add", pkg_requirement)
        if rc != 0:
            await queue.put(
                {"type": "error", "ok": False, "message": f"uv add 返回码: {rc}"}
            )
            return

        if kind in ("plugin", "adapter"):
            if kind == "adapter":
                self._toml_add_adapter(name, module_name)

            data = self._read_manifest(kind)
            packages = data.setdefault("packages", {})
            packages[name] = pkg_requirement
            states = data.setdefault("states", {})
            states[name] = {"enabled": True}
            self._write_manifest(kind, data)
            await self._sync_manifest_env(queue)

        await queue.put(
            {
                "type": "done",
                "ok": True,
                "name": name,
                "message": f"{name} 安装完成",
            }
        )

    async def _do_uninstall(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        kind: str,
        name: str,
        *,
        keep_config: bool,
    ) -> None:
        uv = await self._require_uv(queue)
        if uv is None:
            return

        if kind not in ("plugin", "adapter"):
            pkg_req = name
        else:
            data = self._read_manifest(kind)
            packages = data.get("packages") or {}
            pkg_req = packages.get(name) or name

        await self._emit(queue, "output", f"> uv remove {pkg_req}")
        rc = await self._run_subprocess(queue, uv, "remove", pkg_req)
        if rc != 0:
            await queue.put(
                {"type": "error", "ok": False, "message": f"uv remove 返回码: {rc}"}
            )
            return

        if kind in ("plugin", "adapter"):
            if kind == "plugin":
                from pathlib import Path

                from apeiria.plugin.manager import _is_safe_plugin_name

                local_path = Path(f".apeiria/plugins/{name}").resolve()
                plugins_root = Path(".apeiria/plugins").resolve()
                if (
                    _is_safe_plugin_name(name)
                    and local_path.is_relative_to(plugins_root)
                    and local_path.is_dir()
                ):
                    import shutil as _shutil

                    _shutil.rmtree(local_path, ignore_errors=True)
            else:
                self._toml_remove_adapter(name)

            data = self._read_manifest(kind)
            packages = data.get("packages") or {}
            packages.pop(name, None)
            states = data.get("states") or {}
            states.pop(name, None)
            self._write_manifest(kind, data)

            if not keep_config:
                self._remove_config(kind, name)

            await self._sync_manifest_env(queue)

        await queue.put(
            {
                "type": "done",
                "ok": True,
                "name": name,
                "message": f"{name} 卸载完成",
            }
        )

    async def _do_update(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        kind: str,
        name: str,
        pkg_requirement: str,
    ) -> None:
        uv = await self._require_uv(queue)
        if uv is None:
            return

        await self._emit(queue, "output", f"> uv add {pkg_requirement}")
        rc = await self._run_subprocess(queue, uv, "add", pkg_requirement)
        if rc != 0:
            await queue.put(
                {"type": "error", "ok": False, "message": f"uv add 返回码: {rc}"}
            )
            return

        if kind in ("plugin", "adapter"):
            data = self._read_manifest(kind)
            data.setdefault("packages", {})[name] = pkg_requirement
            self._write_manifest(kind, data)
            await self._sync_manifest_env(queue)

        await queue.put(
            {
                "type": "done",
                "ok": True,
                "name": name,
                "message": f"{name} 更新完成",
            }
        )

    async def _emit(
        self, queue: asyncio.Queue[dict[str, Any]], event_type: str, text: str
    ) -> None:
        await queue.put(
            {
                "type": event_type,
                "text": text,
            }
        )


_runner = TaskRunner()


def get_task_runner() -> TaskRunner:
    return _runner
