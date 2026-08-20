from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from nonebot.log import logger

from apeiria.jobs.base import Job, JobError
from apeiria.jobs.uv import run_uv_add, run_uv_remove, run_uv_sync

_APEIRIA_DIR = Path(".apeiria")


class PackageJob(Job):
    """Install, remove or update a plugin/adapter in the isolated .apeiria env."""

    def __init__(  # noqa: PLR0913
        self,
        kind: str,
        name: str,
        pkg_requirement: str = "",
        *,
        operation: str,
        module_name: str | None = None,
        keep_config: bool = False,
    ) -> None:
        super().__init__(kind="package", lock_name="apeiria")
        self.package_kind = kind
        self.name = name
        self.pkg_requirement = pkg_requirement
        self.operation = operation
        self.module_name = module_name
        self.keep_config = keep_config
        self._snapshot_data: dict[str, str | None] = {}

    def snapshot(self) -> None:
        for path in (
            _APEIRIA_DIR / "plugins.yaml",
            _APEIRIA_DIR / "adapters.yaml",
            _APEIRIA_DIR / "pyproject.toml",
            _APEIRIA_DIR / "uv.lock",
        ):
            self._snapshot_data[str(path)] = _read_text(path)

    async def run(self) -> None:
        if self.operation == "install":
            await self._do_install()
        elif self.operation == "uninstall":
            await self._do_uninstall()
        elif self.operation == "update":
            await self._do_update()
        else:
            msg = f"未知操作: {self.operation}"
            raise JobError(msg)

    async def _do_install(self) -> None:
        rc = await run_uv_add(self, self.pkg_requirement, _APEIRIA_DIR)
        if rc != 0:
            msg = f"uv add 返回码: {rc}"
            raise JobError(msg)

        if self.package_kind not in ("plugin", "adapter"):
            return

        if self.package_kind == "adapter":
            from apeiria.plugin.adapter_manager import _toml_add_adapter

            _toml_add_adapter(self.name, self.module_name or self.name)

        data = _read_manifest(self.package_kind)
        packages = data.setdefault("packages", {})
        packages[self.name] = self.pkg_requirement
        states = data.setdefault("states", {})
        states[self.name] = {"enabled": True}
        _write_manifest(self.package_kind, data)

        rc = await run_uv_sync(self, _APEIRIA_DIR)
        if rc != 0:
            msg = f"uv sync 返回码: {rc}"
            raise JobError(msg)

    async def _do_update(self) -> None:
        rc = await run_uv_add(self, self.pkg_requirement, _APEIRIA_DIR)
        if rc != 0:
            msg = f"uv add 返回码: {rc}"
            raise JobError(msg)

        if self.package_kind not in ("plugin", "adapter"):
            return

        data = _read_manifest(self.package_kind)
        data.setdefault("packages", {})[self.name] = self.pkg_requirement
        _write_manifest(self.package_kind, data)

        rc = await run_uv_sync(self, _APEIRIA_DIR)
        if rc != 0:
            msg = f"uv sync 返回码: {rc}"
            raise JobError(msg)

    async def _do_uninstall(self) -> None:
        if self.package_kind not in ("plugin", "adapter"):
            pkg_req = self.name
        else:
            data = _read_manifest(self.package_kind)
            packages = data.get("packages") or {}
            pkg_req = packages.get(self.name) or self.name

        rc = await run_uv_remove(self, pkg_req, _APEIRIA_DIR)
        if rc != 0:
            msg = f"uv remove 返回码: {rc}"
            raise JobError(msg)

        if self.package_kind == "plugin":
            _remove_local_plugin_dir(self.name)
        elif self.package_kind == "adapter":
            from apeiria.plugin.adapter_manager import _toml_remove_adapter

            _toml_remove_adapter(self.name)

        if self.package_kind in ("plugin", "adapter"):
            data = _read_manifest(self.package_kind)
            packages = data.get("packages") or {}
            packages.pop(self.name, None)
            states = data.get("states") or {}
            states.pop(self.name, None)
            _write_manifest(self.package_kind, data)

            if not self.keep_config:
                _remove_config(self.package_kind, self.name)

            rc = await run_uv_sync(self, _APEIRIA_DIR)
            if rc != 0:
                msg = f"uv sync 返回码: {rc}"
                raise JobError(msg)

    async def rollback(self) -> None:
        if not self._snapshot_data:
            return

        logger.warning("Rolling back package job {}", self.id)
        self.emit(
            {"type": "stage", "stage": "rollback", "line": "正在回滚包管理变更..."}
        )

        for path_str, content in self._snapshot_data.items():
            path = Path(path_str)
            if content is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

        rc = await run_uv_sync(self, _APEIRIA_DIR)
        if rc != 0:
            msg = f"回滚后 uv sync 返回码: {rc}"
            raise JobError(msg)

        self.emit({"type": "stage", "stage": "rollback", "line": "回滚完成"})


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_manifest(kind: str) -> dict[str, Any]:
    if kind == "plugin":
        from apeiria.plugin.manager import _read_plugins_yaml

        return _read_plugins_yaml()
    from apeiria.plugin.adapter_manager import _read_adapters_yaml

    return _read_adapters_yaml()


def _write_manifest(kind: str, data: dict[str, Any]) -> None:
    if kind == "plugin":
        from apeiria.plugin.manager import _write_plugins_yaml

        _write_plugins_yaml(data)
        return
    from apeiria.plugin.adapter_manager import _write_adapters_yaml

    _write_adapters_yaml(data)


def _remove_config(kind: str, name: str) -> None:
    if kind == "plugin":
        from apeiria.plugin.manager import _remove_plugin_config

        _remove_plugin_config(name)
        return
    from apeiria.plugin.adapter_manager import _remove_adapter_config

    _remove_adapter_config(name)


def _remove_local_plugin_dir(name: str) -> None:
    from apeiria.plugin.manager import _is_safe_plugin_name

    local_path = Path(f".apeiria/plugins/{name}").resolve()
    plugins_root = Path(".apeiria/plugins").resolve()
    if (
        _is_safe_plugin_name(name)
        and local_path.is_relative_to(plugins_root)
        and local_path.is_dir()
    ):
        shutil.rmtree(local_path, ignore_errors=True)
