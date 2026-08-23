"""Install, uninstall, and manage plugins in the Apeiria environment."""

from __future__ import annotations

from pathlib import Path

import yaml
from nonebot.log import logger

from apeiria.env.sync import sync_apeiria_env
from apeiria.jobs.uv import find_uv


def _read_plugins_yaml() -> dict:
    """Read plugin package and state records from ``plugins.yaml``.

    Returns:
        A dict with ``dirs``, ``packages``, and ``states`` keys, or an empty
        structure if the file does not exist.
    """
    p = Path(".apeiria/plugins.yaml")
    if not p.exists():
        return {"dirs": [], "packages": {}, "states": {}}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _write_plugins_yaml(data: dict) -> None:
    """Write plugin package and state records to ``plugins.yaml``.

    Args:
        data: The plugin data dict to persist.
    """
    p = Path(".apeiria/plugins.yaml")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def _is_safe_plugin_name(name: str) -> bool:
    """Return whether a plugin name is safe to use as a local directory.

    Args:
        name: The plugin name to validate.

    Returns:
        ``True`` if the name is non-empty and free of path separators.
    """
    return (
        bool(name) and name not in {".", ".."} and "/" not in name and "\\" not in name
    )


def install_plugin(name: str, pkg_requirement: str) -> tuple[bool, str]:
    """Install a plugin package into the Apeiria environment.

    Args:
        name: The plugin name.
        pkg_requirement: The package requirement to install.

    Returns:
        ``(True, message)`` on success, or ``(False, error)`` on failure.
    """
    import subprocess

    uv = find_uv()
    if uv is None:
        return False, "uv not found"

    try:
        result = subprocess.run(
            [uv, "add", "--directory", ".apeiria", pkg_requirement],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, "安装超时（120s），请检查网络或包大小"
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        logger.error("uv add failed: {}", err)
        return False, err

    data = _read_plugins_yaml()
    packages = data.setdefault("packages", {})
    packages[name] = pkg_requirement
    states = data.setdefault("states", {})
    states[name] = {"enabled": True}
    _write_plugins_yaml(data)

    sync_apeiria_env()
    return True, "安装成功"


def uninstall_plugin(name: str, *, keep_config: bool = False) -> bool:
    """Uninstall a plugin package from the Apeiria environment.

    Args:
        name: The plugin name to remove.
        keep_config: If ``True``, keep the plugin's ``config.yaml`` section.

    Returns:
        ``True`` if the plugin was removed, ``False`` if it was not found.
    """
    import subprocess

    data = _read_plugins_yaml()
    packages = data.get("packages") or {}
    pkg = packages.get(name, "")
    if not pkg:
        logger.warning("Plugin {} not found in plugins.yaml", name)
        return False

    uv = find_uv()
    if uv is not None:
        subprocess.run(
            [uv, "remove", "--directory", ".apeiria", pkg],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    packages.pop(name, None)
    states = data.get("states") or {}
    states.pop(name, None)
    _write_plugins_yaml(data)

    local_path = Path(f".apeiria/plugins/{name}").resolve()
    plugins_root = Path(".apeiria/plugins").resolve()
    if (
        _is_safe_plugin_name(name)
        and local_path.is_relative_to(plugins_root)
        and local_path.is_dir()
    ):
        import shutil as _shutil

        _shutil.rmtree(local_path, ignore_errors=True)

    if not keep_config:
        _remove_plugin_config(name)

    sync_apeiria_env()
    return True


def set_plugin_state(name: str, enabled: bool) -> bool:  # noqa: FBT001
    """Set the enabled state for a plugin.

    Args:
        name: The plugin name.
        enabled: Whether the plugin should be enabled.

    Returns:
        ``True`` when the state is recorded.
    """
    data = _read_plugins_yaml()
    states = data.setdefault("states", {})
    states[name] = {"enabled": enabled}
    _write_plugins_yaml(data)
    return True


def _remove_plugin_config(name: str) -> None:
    """Remove a plugin's configuration section from ``config.yaml``.

    Args:
        name: The plugin name whose config should be dropped.
    """
    config_path = Path("data/config.yaml")
    if not config_path.exists():
        return
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    plugins = raw.get("plugins")
    if isinstance(plugins, dict):
        plugins.pop(name, None)
        config_path.write_text(
            yaml.dump(raw, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
