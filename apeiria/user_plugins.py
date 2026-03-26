from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

from apeiria.core.utils.files import atomic_write_text, load_toml_dict
from apeiria.core.utils.package_config import (
    add_unique_sorted_item,
    bind_package_item,
    get_package_bound_items,
    normalize_package_item_map,
    normalize_string_list,
    remove_item_from_config_packages,
    unbind_package_item,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class UserPluginConfig(TypedDict):
    modules: list[str]
    dirs: list[str]
    packages: dict[str, list[str]]


logger = logging.getLogger("apeiria.user_plugins")


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "apeiria.plugins.toml"


def _normalize_str_list(value: object) -> list[str]:
    return normalize_string_list(value, ignore_literal_null=True)


def _load_config(config_path: Path) -> dict[str, Any]:
    return load_toml_dict(
        config_path,
        logger=logger,
        missing_dependency_message=(
            "Skip loading apeiria.plugins.toml: tomllib/tomli is unavailable"
        ),
    )


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
    return normalize_package_item_map(value)


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
    atomic_write_text(target, _dump_config(config))
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
    if add_unique_sorted_item(config["modules"], module_name):
        write_project_plugin_config(config, config_path)
    return config


def remove_project_plugin_module(
    module_name: str,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    remove_item_from_config_packages(
        cast("dict[str, Any]", config),
        items_key="modules",
        item=module_name,
    )
    write_project_plugin_config(config, config_path)
    return config


def add_project_plugin_dir(
    directory: str,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    if add_unique_sorted_item(config["dirs"], directory):
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
    bind_package_item(
        cast("dict[str, Any]", config),
        package_name=package_name,
        item=module_name,
    )
    write_project_plugin_config(config, config_path)
    return config


def get_project_plugin_package_modules(
    package_name: str,
    config_path: Path | None = None,
) -> list[str]:
    config = read_project_plugin_config(config_path)
    return get_package_bound_items(
        cast("dict[str, Any]", config),
        package_name=package_name,
    )


def unbind_project_plugin_package(
    package_name: str,
    module_name: str | None = None,
    config_path: Path | None = None,
) -> UserPluginConfig:
    config = read_project_plugin_config(config_path)
    changed = unbind_package_item(
        cast("dict[str, Any]", config),
        package_name=package_name,
        items_key="modules",
        item=module_name,
    )
    if not changed:
        return config
    write_project_plugin_config(config, config_path)
    return config
