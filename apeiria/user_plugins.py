from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from apeiria.package_ids import normalize_package_id

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


class UserPluginConfig(TypedDict):
    modules: list[str]
    dirs: list[str]
    packages: dict[str, list[str]]


logger = logging.getLogger("apeiria.user_plugins")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_config_path() -> Path:
    return _project_root() / "apeiria.plugins.toml"


def _normalize_str_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if not normalized or normalized.lower() in {"none", "null"}:
            continue
        result.append(normalized)
    return result


def _load_config(config_path: Path) -> dict[str, Any]:
    if tomllib is None:
        logger.warning(
            "Skip loading apeiria.plugins.toml: tomllib/tomli is unavailable"
        )
        return {}
    if not config_path.is_file():
        return {}

    try:
        with config_path.open("rb") as file:
            data = tomllib.load(file)
    except OSError as exc:
        logger.warning(
            "Skip loading %s: %s",
            config_path.name,
            exc,
        )
        return {}
    except tomllib.TOMLDecodeError as exc:
        logger.warning(
            "Skip loading %s: invalid TOML (%s)",
            config_path.name,
            exc,
        )
        return {}

    return data if isinstance(data, dict) else {}


def _normalize_config(data: dict[str, Any]) -> UserPluginConfig:
    plugin_config = data.get("plugins")
    if not isinstance(plugin_config, dict):
        return {"modules": [], "dirs": [], "packages": {}}
    package_config = data.get("plugin_packages")
    return {
        "modules": _normalize_str_list(plugin_config.get("modules")),
        "dirs": _normalize_str_list(plugin_config.get("dirs")),
        "packages": _normalize_package_map(package_config),
    }


def _dump_config(config: UserPluginConfig) -> str:
    def _dump_list(values: Sequence[str]) -> str:
        return ", ".join(f'"{value}"' for value in values)

    lines = [
        "[plugins]",
        f"modules = [{_dump_list(config['modules'])}]",
        f"dirs = [{_dump_list(config['dirs'])}]",
        "",
    ]
    if config["packages"]:
        lines.append("[plugin_packages]")
        lines.extend(
            f'"{package_name}" = [{_dump_list(config["packages"][package_name])}]'
            for package_name in sorted(config["packages"])
        )
        lines.append("")
    return "\n".join(lines)


def _normalize_package_map(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, list[str]] = {}
    for package_name, modules in value.items():
        if not isinstance(package_name, str) or not package_name.strip():
            continue
        normalized_modules = sorted(set(_normalize_str_list(modules)))
        normalized_package = normalize_package_id(package_name)
        if normalized_package and normalized_modules:
            result[normalized_package] = normalized_modules
    return result


def _resolve_dirs(config_path: Path, directories: Sequence[str]) -> list[Path]:
    base_dir = config_path.parent
    resolved_dirs: list[Path] = []
    for raw_dir in directories:
        path = Path(raw_dir).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        resolved_dirs.append(path.resolve())
    return resolved_dirs


def default_config_path() -> Path:
    return _default_config_path()


def read_project_plugin_config(config_path: Path | None = None) -> UserPluginConfig:
    target = config_path or _default_config_path()
    return _normalize_config(_load_config(target))


def write_project_plugin_config(
    config: UserPluginConfig,
    config_path: Path | None = None,
) -> Path:
    target = config_path or _default_config_path()
    target.write_text(_dump_config(config), encoding="utf-8")
    return target


def ensure_project_plugin_config(config_path: Path | None = None) -> Path:
    target = config_path or _default_config_path()
    if not target.exists():
        write_project_plugin_config({"modules": [], "dirs": [], "packages": {}}, target)
    return target


def add_project_plugin_module(
    module_name: str,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    if module_name not in config["modules"]:
        config["modules"].append(module_name)
        config["modules"].sort()
        write_project_plugin_config(config, config_path)
    return config


def remove_project_plugin_module(
    module_name: str,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    config["modules"] = [item for item in config["modules"] if item != module_name]
    for package_name in list(config["packages"]):
        config["packages"][package_name] = [
            item for item in config["packages"][package_name] if item != module_name
        ]
        if not config["packages"][package_name]:
            del config["packages"][package_name]
    write_project_plugin_config(config, config_path)
    return config


def add_project_plugin_dir(
    directory: str,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    if directory not in config["dirs"]:
        config["dirs"].append(directory)
        config["dirs"].sort()
        write_project_plugin_config(config, config_path)
    return config


def remove_project_plugin_dir(
    directory: str,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    config["dirs"] = [item for item in config["dirs"] if item != directory]
    write_project_plugin_config(config, config_path)
    return config


def load_project_plugins(config_path: Path | None = None) -> None:
    target = config_path or _default_config_path()
    config = read_project_plugin_config(target)
    modules = config["modules"]
    directories = _resolve_dirs(target, config["dirs"])

    import nonebot

    loaded_modules = {
        plugin.module_name
        for plugin in nonebot.get_loaded_plugins()
        if getattr(plugin, "module_name", None)
    }
    modules = [module for module in modules if module not in loaded_modules]

    existing_dirs: list[str] = []
    for directory in directories:
        if not directory.is_dir():
            logger.warning(
                "Skip loading plugin dir %s: directory not found",
                directory,
            )
            continue
        existing_dirs.append(str(directory))

    nonebot.load_all_plugins(modules, existing_dirs)


def bind_project_plugin_package(
    package_name: str,
    module_name: str,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = add_project_plugin_module(module_name, config_path)
    package_key = normalize_package_id(package_name)
    if not package_key:
        return config
    modules = set(config["packages"].get(package_key, []))
    modules.add(module_name)
    config["packages"][package_key] = sorted(modules)
    write_project_plugin_config(config, config_path)
    return config


def get_project_plugin_package_modules(
    package_name: str,
    config_path: Path | None = None,
) -> list[str]:
    config = read_project_plugin_config(config_path)
    return list(config["packages"].get(normalize_package_id(package_name), []))


def unbind_project_plugin_package(
    package_name: str,
    module_name: str | None = None,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    package_key = normalize_package_id(package_name)
    if not package_key:
        return config
    if module_name is None:
        modules = config["packages"].pop(package_key, [])
        for item in modules:
            config["modules"] = [
                module for module in config["modules"] if module != item
            ]
        write_project_plugin_config(config, config_path)
        return config
    modules = config["packages"].get(package_key, [])
    if not modules:
        return config
    config["packages"][package_key] = [item for item in modules if item != module_name]
    if not config["packages"][package_key]:
        del config["packages"][package_key]
    config["modules"] = [item for item in config["modules"] if item != module_name]
    write_project_plugin_config(config, config_path)
    return config
