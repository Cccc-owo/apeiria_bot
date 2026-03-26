from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, TypedDict, cast

from apeiria.core.utils.files import atomic_write_text, load_toml_dict
from apeiria.core.utils.package_config import (
    bind_package_item,
    get_package_bound_items,
    normalize_package_item_map,
    normalize_string_list,
    remove_item_from_config_packages,
    unbind_package_item,
)


class UserDriverConfig(TypedDict):
    builtin: list[str]
    packages: dict[str, list[str]]


logger = logging.getLogger("apeiria.user_drivers")


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "apeiria.drivers.toml"


def _normalize_str_list(value: object) -> list[str]:
    return normalize_string_list(value)


def _load_config(config_path: Path) -> dict[str, Any]:
    return load_toml_dict(
        config_path,
        logger=logger,
        missing_dependency_message=(
            "Skip loading apeiria.drivers.toml: tomllib/tomli is unavailable"
        ),
    )


def _normalize_config(data: dict[str, Any]) -> UserDriverConfig:
    driver_config = data.get("drivers")
    if not isinstance(driver_config, dict):
        return {"builtin": [], "packages": {}}
    package_config = data.get("driver_packages")
    return {
        "builtin": _normalize_str_list(driver_config.get("builtin")),
        "packages": _normalize_package_map(package_config),
    }


def _dump_config(config: UserDriverConfig) -> str:
    builtin = ", ".join(f'"{item}"' for item in config["builtin"])
    lines = [
        "[drivers]",
        f"builtin = [{builtin}]",
        "",
    ]
    if config["packages"]:
        lines.append("[driver_packages]")
        for package_name in sorted(config["packages"]):
            mapped = ", ".join(f'"{item}"' for item in config["packages"][package_name])
            lines.append(f'"{package_name}" = [{mapped}]')
        lines.append("")
    return "\n".join(lines)


def _normalize_package_map(value: object) -> dict[str, list[str]]:
    return normalize_package_item_map(value)


def default_config_path() -> Path:
    return _default_config_path()


def read_project_driver_config(config_path: Path | None = None) -> UserDriverConfig:
    target = config_path or _default_config_path()
    return _normalize_config(_load_config(target))


def write_project_driver_config(
    config: UserDriverConfig,
    config_path: Path | None = None,
) -> Path:
    target = config_path or _default_config_path()
    atomic_write_text(target, _dump_config(config))
    return target


def ensure_project_driver_config(config_path: Path | None = None) -> Path:
    target = config_path or _default_config_path()
    if not target.exists():
        write_project_driver_config({"builtin": [], "packages": {}}, target)
    return target


def add_project_driver_builtin(
    builtin_name: str,
    config_path: Path | None = None,
) -> UserDriverConfig:
    config = read_project_driver_config(config_path)
    if builtin_name not in config["builtin"]:
        config["builtin"] = _merge_driver_builtin(config["builtin"], builtin_name)
        write_project_driver_config(config, config_path)
    return config


def remove_project_driver_builtin(
    builtin_name: str,
    config_path: Path | None = None,
) -> UserDriverConfig:
    config = read_project_driver_config(config_path)
    remove_item_from_config_packages(
        cast("dict[str, Any]", config),
        items_key="builtin",
        item=builtin_name,
    )
    write_project_driver_config(config, config_path)
    return config


def get_project_driver_kwargs(config_path: Path | None = None) -> dict[str, str]:
    config = read_project_driver_config(config_path)
    builtin = effective_driver_builtin(config["builtin"])
    if not builtin:
        return {}
    return {"driver": "+".join(builtin)}


def bind_project_driver_package(
    package_name: str,
    builtin_name: str,
    config_path: Path | None = None,
) -> UserDriverConfig:
    config = add_project_driver_builtin(builtin_name, config_path)
    bind_package_item(
        cast("dict[str, Any]", config),
        package_name=package_name,
        item=builtin_name,
    )
    write_project_driver_config(config, config_path)
    return config


def get_project_driver_package_builtin(
    package_name: str,
    config_path: Path | None = None,
) -> list[str]:
    config = read_project_driver_config(config_path)
    return get_package_bound_items(
        cast("dict[str, Any]", config),
        package_name=package_name,
    )


def unbind_project_driver_package(
    package_name: str,
    builtin_name: str | None = None,
    config_path: Path | None = None,
) -> UserDriverConfig:
    config = read_project_driver_config(config_path)
    changed = unbind_package_item(
        cast("dict[str, Any]", config),
        package_name=package_name,
        items_key="builtin",
        item=builtin_name,
    )
    if not changed:
        return config
    write_project_driver_config(config, config_path)
    return config


def effective_driver_builtin(builtin: list[str]) -> list[str]:
    normalized = [item for item in builtin if item]
    if not normalized:
        return []

    capabilities = {item: _driver_builtin_capabilities(item) for item in normalized}
    pure_drivers = [
        item
        for item in normalized
        if capabilities[item]["driver"] and not capabilities[item]["mixin"]
    ]
    if pure_drivers:
        primary = pure_drivers[-1]
        mixins = [
            item
            for item in normalized
            if item != primary and capabilities[item]["mixin"]
        ]
        return [primary, *mixins]

    hybrid = next(
        (item for item in normalized if capabilities[item]["driver"]),
        None,
    )
    if hybrid is not None:
        mixins = [
            item
            for item in normalized
            if item != hybrid and capabilities[item]["mixin"]
        ]
        return [hybrid, *mixins]

    return normalized


def _merge_driver_builtin(current: list[str], builtin_name: str) -> list[str]:
    combined = [item for item in current if item != builtin_name]
    combined.append(builtin_name)
    return effective_driver_builtin(combined)


def _driver_builtin_capabilities(builtin_name: str) -> dict[str, bool]:
    module_name = builtin_name.strip().removeprefix("~")
    if not module_name:
        return {"driver": False, "mixin": False}

    try:
        from apeiria.user_plugin_env import inject_plugin_site_packages

        inject_plugin_site_packages()
        module = importlib.import_module(f"nonebot.drivers.{module_name}")
    except ImportError:
        return {"driver": False, "mixin": False}

    return {
        "driver": hasattr(module, "Driver"),
        "mixin": hasattr(module, "Mixin"),
    }
