from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypedDict, cast

import nonebot
from nonebot.utils import resolve_dot_notation

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


class UserAdapterConfig(TypedDict):
    modules: list[str]
    packages: dict[str, list[str]]


logger = logging.getLogger("apeiria.user_adapters")


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "apeiria.adapters.toml"


def _normalize_str_list(value: object) -> list[str]:
    return normalize_string_list(value)


def _load_config(config_path: Path) -> dict[str, Any]:
    return load_toml_dict(
        config_path,
        logger=logger,
        missing_dependency_message=(
            "Skip loading apeiria.adapters.toml: tomllib/tomli is unavailable"
        ),
    )


def _normalize_config(data: dict[str, Any]) -> UserAdapterConfig:
    adapter_config = data.get("adapters")
    if not isinstance(adapter_config, dict):
        return {"modules": [], "packages": {}}
    package_config = data.get("adapter_packages")
    return {
        "modules": _normalize_str_list(adapter_config.get("modules")),
        "packages": _normalize_package_map(package_config),
    }


def _dump_config(config: UserAdapterConfig) -> str:
    modules = ", ".join(f'"{module}"' for module in config["modules"])
    lines = [
        "[adapters]",
        f"modules = [{modules}]",
        "",
    ]
    if config["packages"]:
        lines.append("[adapter_packages]")
        for package_name in sorted(config["packages"]):
            package_modules = config["packages"][package_name]
            mapped = ", ".join(f'"{module}"' for module in package_modules)
            lines.append(f'"{package_name}" = [{mapped}]')
        lines.append("")
    return "\n".join(lines)


def _normalize_package_map(value: object) -> dict[str, list[str]]:
    return normalize_package_item_map(value)


def default_config_path() -> Path:
    return _default_config_path()


def read_project_adapter_config(config_path: Path | None = None) -> UserAdapterConfig:
    target = config_path or _default_config_path()
    return _normalize_config(_load_config(target))


def write_project_adapter_config(
    config: UserAdapterConfig,
    config_path: Path | None = None,
) -> Path:
    target = config_path or _default_config_path()
    atomic_write_text(target, _dump_config(config))
    return target


def ensure_project_adapter_config(config_path: Path | None = None) -> Path:
    target = config_path or _default_config_path()
    if not target.exists():
        write_project_adapter_config({"modules": [], "packages": {}}, target)
    return target


def add_project_adapter_module(
    module_name: str,
    config_path: Path | None = None,
) -> UserAdapterConfig:
    config = read_project_adapter_config(config_path)
    if add_unique_sorted_item(config["modules"], module_name):
        write_project_adapter_config(config, config_path)
    return config


def remove_project_adapter_module(
    module_name: str,
    config_path: Path | None = None,
) -> UserAdapterConfig:
    config = read_project_adapter_config(config_path)
    remove_item_from_config_packages(
        cast("dict[str, Any]", config),
        items_key="modules",
        item=module_name,
    )
    write_project_adapter_config(config, config_path)
    return config


def _is_adapter_registered(driver: object, adapter_cls: type[object]) -> bool:
    _ = driver
    adapters = nonebot.get_adapters()
    return any(
        registered is adapter_cls
        or (
            getattr(registered, "__module__", None) == adapter_cls.__module__
            and getattr(registered, "__name__", None) == adapter_cls.__name__
        )
        for registered in adapters.values()
    )


def load_project_adapters(
    driver: object,
    config_path: Path | None = None,
) -> None:
    config = read_project_adapter_config(config_path)
    register = getattr(driver, "register_adapter", None)
    if not callable(register):
        logger.warning(
            "Skip loading apeiria.adapters.toml: driver has no register_adapter"
        )
        return

    for module_name in config["modules"]:
        try:
            adapter_cls = resolve_dot_notation(module_name, "Adapter")
        except (ImportError, AttributeError, ValueError) as exc:
            logger.warning("Skip adapter %s: %s", module_name, exc)
            continue

        if _is_adapter_registered(driver, adapter_cls):
            logger.debug("Skip adapter %s: already registered", module_name)
            continue

        register(adapter_cls)


def bind_project_adapter_package(
    package_name: str,
    module_name: str,
    config_path: Path | None = None,
) -> UserAdapterConfig:
    config = add_project_adapter_module(module_name, config_path)
    bind_package_item(
        cast("dict[str, Any]", config),
        package_name=package_name,
        item=module_name,
    )
    write_project_adapter_config(config, config_path)
    return config


def get_project_adapter_package_modules(
    package_name: str,
    config_path: Path | None = None,
) -> list[str]:
    config = read_project_adapter_config(config_path)
    return get_package_bound_items(
        cast("dict[str, Any]", config),
        package_name=package_name,
    )


def unbind_project_adapter_package(
    package_name: str,
    module_name: str | None = None,
    config_path: Path | None = None,
) -> UserAdapterConfig:
    config = read_project_adapter_config(config_path)
    changed = unbind_package_item(
        cast("dict[str, Any]", config),
        package_name=package_name,
        items_key="modules",
        item=module_name,
    )
    if not changed:
        return config
    write_project_adapter_config(config, config_path)
    return config
