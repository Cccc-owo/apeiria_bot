"""System health checks shared by CLI and future management surfaces."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from apeiria.core.utils.webui_build import read_frontend_build_status

_CHECK_MESSAGES: dict[tuple[str, str], tuple[str, str | None]] = {
    ("uv", "available"): ("uv is available.", None),
    ("uv", "missing"): (
        "uv is not installed.",
        "Install uv, then run `apeiria env init`.",
    ),
    ("main_config", "present"): ("Project config file is present.", None),
    ("main_config", "missing"): (
        "Missing `apeiria.config.toml`.",
        "Copy `apeiria.config.example.toml` to `apeiria.config.toml`.",
    ),
    ("plugin_config", "present"): ("Plugin config file is present.", None),
    ("plugin_config", "missing"): (
        "Missing `apeiria.plugins.toml`.",
        "Copy `apeiria.plugins.example.toml` to `apeiria.plugins.toml`.",
    ),
    ("adapter_config", "present"): ("Adapter config file is present.", None),
    ("adapter_config", "missing"): (
        "Missing `apeiria.adapters.toml`.",
        "Copy `apeiria.adapters.example.toml` to `apeiria.adapters.toml`.",
    ),
    ("driver_config", "present"): ("Driver config file is present.", None),
    ("driver_config", "missing"): (
        "Missing `apeiria.drivers.toml`.",
        "Copy `apeiria.drivers.example.toml` to `apeiria.drivers.toml`.",
    ),
    ("main_venv", "present"): ("Main Python environment is present.", None),
    ("main_venv", "missing"): (
        "Main project virtual environment is missing.",
        "Run `uv sync --locked` or `apeiria env init`.",
    ),
    ("extension_project", "present"): (
        "Extension environment project is present.",
        None,
    ),
    ("extension_project", "missing"): (
        "Managed extension project is missing.",
        "Run `apeiria env init` to create `.apeiria/extensions`.",
    ),
    ("frontend_workspace", "present"): ("Frontend workspace is present.", None),
    ("frontend_workspace", "missing"): (
        "Frontend workspace is missing.",
        "Restore the `web/` directory if you need the Web UI.",
    ),
    ("frontend_toolchain", "missing"): (
        "No frontend package manager was found.",
        "Install pnpm or npm to rebuild Web UI assets.",
    ),
    ("frontend_build", "current"): ("Web UI build artifacts are up to date.", None),
    ("frontend_build", "dist_missing"): (
        "Web UI build artifacts are missing.",
        "Run `apeiria run --build` or `cd web && pnpm build`.",
    ),
    ("frontend_build", "build_meta_missing"): (
        "Web UI build metadata is missing.",
        "Rebuild the frontend once to refresh build metadata.",
    ),
    ("frontend_build", "fingerprint_missing"): (
        "Web UI build fingerprint is missing.",
        "Rebuild the frontend once to restore build metadata.",
    ),
    ("frontend_build", "stale"): (
        "Web UI build artifacts are outdated.",
        "Run `apeiria run --build` before using the Web UI.",
    ),
}


@dataclass(frozen=True)
class SystemHealthCheck:
    """One environment or runtime health check."""

    key: str
    ok: bool
    detail: str
    message: str = ""
    hint: str | None = None


@dataclass(frozen=True)
class SystemHealthSnapshot:
    """Aggregated system health summary."""

    status: str
    project_root: Path
    checks: list[SystemHealthCheck]


class SystemHealthService:
    """Inspect the local Apeiria workspace without mutating it."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = (
            project_root
            if project_root is not None
            else Path(__file__).resolve().parent.parent.parent.parent
        )

    def get_snapshot(self) -> SystemHealthSnapshot:
        """Collect environment checks for CLI diagnostics."""
        root = self._project_root
        web_dir = root / "web"
        extension_root = root / ".apeiria" / "extensions"
        build_status = read_frontend_build_status(root)
        uv_executable = shutil.which("uv")
        package_manager = shutil.which("pnpm") or shutil.which("npm")

        checks = [
            self._build_check(
                key="uv",
                ok=uv_executable is not None,
                detail="available" if uv_executable is not None else "missing",
            ),
            self._build_check(
                key="main_config",
                ok=(root / "apeiria.config.toml").is_file(),
                detail="present"
                if (root / "apeiria.config.toml").is_file()
                else "missing",
            ),
            self._build_check(
                key="plugin_config",
                ok=(root / "apeiria.plugins.toml").is_file(),
                detail="present"
                if (root / "apeiria.plugins.toml").is_file()
                else "missing",
            ),
            self._build_check(
                key="adapter_config",
                ok=(root / "apeiria.adapters.toml").is_file(),
                detail="present"
                if (root / "apeiria.adapters.toml").is_file()
                else "missing",
            ),
            self._build_check(
                key="driver_config",
                ok=(root / "apeiria.drivers.toml").is_file(),
                detail="present"
                if (root / "apeiria.drivers.toml").is_file()
                else "missing",
            ),
            self._build_check(
                key="main_venv",
                ok=(root / ".venv").is_dir(),
                detail="present" if (root / ".venv").is_dir() else "missing",
            ),
            self._build_check(
                key="extension_project",
                ok=(extension_root / "pyproject.toml").is_file(),
                detail="present"
                if (extension_root / "pyproject.toml").is_file()
                else "missing",
            ),
            self._build_check(
                key="frontend_workspace",
                ok=(web_dir / "package.json").is_file(),
                detail="present" if (web_dir / "package.json").is_file() else "missing",
            ),
            self._build_check(
                key="frontend_toolchain",
                ok=(
                    not (web_dir / "package.json").is_file()
                    or package_manager is not None
                ),
                detail=(
                    Path(package_manager).name
                    if package_manager is not None
                    else "missing"
                ),
            ),
            self._build_check(
                key="frontend_build",
                ok=build_status.is_built and not build_status.is_stale,
                detail=build_status.detail,
            ),
        ]
        status = "ok" if all(check.ok for check in checks) else "warning"
        return SystemHealthSnapshot(status=status, project_root=root, checks=checks)

    def _build_check(
        self,
        *,
        key: str,
        ok: bool,
        detail: str,
    ) -> SystemHealthCheck:
        message, hint = self._describe_check(key=key, ok=ok, detail=detail)
        return SystemHealthCheck(
            key=key,
            ok=ok,
            detail=detail,
            message=message,
            hint=hint,
        )

    def _describe_check(
        self,
        *,
        key: str,
        ok: bool,
        detail: str,
    ) -> tuple[str, str | None]:
        if key == "frontend_toolchain" and ok:
            return (f"Frontend build tool is available: {detail}.", None)
        if message := _CHECK_MESSAGES.get((key, detail)):
            return message
        return (f"Check `{key}` is {detail}.", None)


system_health_service = SystemHealthService()
