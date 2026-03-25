from __future__ import annotations

import os
import site
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Final

from apeiria.package_ids import normalize_package_id

_PLUGIN_PROJECT_RELATIVE_PATH: Final = Path(".apeiria") / "extensions"
_PLUGIN_PROJECT_NAME: Final = "apeiria-user-plugins"
_PYTHON_VERSION_FALLBACK: Final = ">=3.10, <4.0"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def plugin_project_root() -> Path:
    return _project_root() / _PLUGIN_PROJECT_RELATIVE_PATH


def plugin_project_exists() -> bool:
    return plugin_project_pyproject_path().is_file()


def plugin_project_pyproject_path() -> Path:
    return plugin_project_root() / "pyproject.toml"


def plugin_project_lock_path() -> Path:
    return plugin_project_root() / "uv.lock"


def plugin_project_venv_path() -> Path:
    return plugin_project_root() / ".venv"


def uv_cache_dir() -> Path:
    return _project_root() / ".apeiria" / "cache" / "uv"


def _main_requires_python() -> str:
    pyproject_path = _project_root() / "pyproject.toml"
    try:
        import tomllib

        with pyproject_path.open("rb") as file:
            data = tomllib.load(file)
    except (ModuleNotFoundError, OSError, ValueError):
        return _PYTHON_VERSION_FALLBACK

    project = data.get("project")
    if not isinstance(project, dict):
        return _PYTHON_VERSION_FALLBACK
    requires_python = project.get("requires-python")
    if not isinstance(requires_python, str) or not requires_python.strip():
        return _PYTHON_VERSION_FALLBACK
    return requires_python.strip()


def _plugin_project_template() -> str:
    requires_python = _main_requires_python()
    return "\n".join(
        [
            "[project]",
            f'name = "{_PLUGIN_PROJECT_NAME}"',
            'version = "0.0.0"',
            f'requires-python = "{requires_python}"',
            "dependencies = []",
            "",
            "[tool.uv]",
            "package = false",
            "",
        ]
    )


def ensure_plugin_project() -> Path:
    root = plugin_project_root()
    root.mkdir(parents=True, exist_ok=True)
    pyproject_path = plugin_project_pyproject_path()
    if not pyproject_path.exists():
        pyproject_path.write_text(_plugin_project_template(), encoding="utf-8")
    return root


def find_uv_executable() -> str:
    executable = which("uv")
    if executable is None:
        msg = "uv is required but was not found in PATH"
        raise RuntimeError(msg)
    return executable


def _run_uv(args: list[str], *, cwd: Path) -> None:
    executable = find_uv_executable()
    cache_dir = uv_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(cache_dir)
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run([executable, *args], cwd=cwd, check=False, env=env)
    if result.returncode != 0:
        msg = f"uv command failed: {' '.join(args)}"
        raise RuntimeError(msg)


def sync_plugin_project(*, locked: bool = True) -> Path:
    root = ensure_plugin_project()
    args = ["sync"]
    if locked and plugin_project_lock_path().exists():
        args.append("--locked")
    _run_uv(args, cwd=root)
    return root


def add_plugin_requirement(requirement: str, extra_args: tuple[str, ...] = ()) -> None:
    root = ensure_plugin_project()
    _run_uv(["add", requirement, *extra_args], cwd=root)


def update_plugin_requirement(
    requirement: str,
    extra_args: tuple[str, ...] = (),
) -> None:
    root = ensure_plugin_project()
    _run_uv(["add", "--upgrade", requirement, *extra_args], cwd=root)


def remove_plugin_requirement(
    requirement: str,
    extra_args: tuple[str, ...] = (),
) -> None:
    root = ensure_plugin_project()
    _run_uv(["remove", requirement, *extra_args], cwd=root)


def declared_plugin_requirements() -> dict[str, str]:
    pyproject_path = plugin_project_pyproject_path()
    try:
        import tomllib

        with pyproject_path.open("rb") as file:
            data = tomllib.load(file)
    except (ModuleNotFoundError, OSError, ValueError):
        return {}

    project = data.get("project")
    if not isinstance(project, dict):
        return {}

    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list):
        return {}

    declared: dict[str, str] = {}
    for item in dependencies:
        if not isinstance(item, str):
            continue
        normalized = normalize_package_id(item)
        if normalized:
            declared[normalized] = item
    return declared


def resolve_declared_plugin_requirement(requirement: str) -> str:
    normalized = normalize_package_id(requirement)
    if not normalized:
        return requirement
    return declared_plugin_requirements().get(normalized, requirement)


def plugin_site_packages_paths() -> list[Path]:
    venv = plugin_project_venv_path()
    if not venv.exists():
        return []

    candidates = [
        path
        for pattern in ("lib/python*/site-packages", "Lib/site-packages")
        for path in venv.glob(pattern)
    ]
    return [path.resolve() for path in candidates if path.is_dir()]


def inject_plugin_site_packages() -> list[Path]:
    added: list[Path] = []
    for path in plugin_site_packages_paths():
        if str(path) in site.getsitepackages():
            continue
        if str(path) in sys.path:
            continue
        site.addsitedir(str(path))
        _extend_loaded_nonebot_package(path)
        added.append(path)
    return added


def _extend_loaded_nonebot_package(site_packages: Path) -> None:
    _extend_loaded_package_path("nonebot", site_packages / "nonebot")
    _extend_loaded_package_path(
        "nonebot.adapters",
        site_packages / "nonebot" / "adapters",
    )
    _extend_loaded_package_path(
        "nonebot.drivers",
        site_packages / "nonebot" / "drivers",
    )


def _extend_loaded_package_path(module_name: str, package_dir: Path) -> None:
    module = sys.modules.get(module_name)
    if module is None or not package_dir.is_dir():
        return

    package_path = getattr(module, "__path__", None)
    if package_path is None:
        return

    normalized = str(package_dir)
    if normalized not in package_path:
        package_path.append(normalized)
