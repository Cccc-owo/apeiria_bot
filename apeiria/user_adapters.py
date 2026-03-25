from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypedDict

import nonebot
from nonebot.utils import resolve_dot_notation

from apeiria.package_ids import normalize_package_id

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


class UserAdapterConfig(TypedDict):
    modules: list[str]
    packages: dict[str, list[str]]


logger = logging.getLogger("apeiria.user_adapters")


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "apeiria.adapters.toml"


def _normalize_str_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _load_config(config_path: Path) -> dict[str, Any]:
    if tomllib is None:
        logger.warning(
            "Skip loading apeiria.adapters.toml: tomllib/tomli is unavailable"
        )
        return {}
    if not config_path.is_file():
        return {}

    try:
        with config_path.open("rb") as file:
            data = tomllib.load(file)
    except OSError as exc:
        logger.warning("Skip loading %s: %s", config_path.name, exc)
        return {}
    except tomllib.TOMLDecodeError as exc:
        logger.warning("Skip loading %s: invalid TOML (%s)", config_path.name, exc)
        return {}

    return data if isinstance(data, dict) else {}


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
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_dump_config(config), encoding="utf-8")
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
    if module_name not in config["modules"]:
        config["modules"].append(module_name)
        config["modules"].sort()
        write_project_adapter_config(config, config_path)
    return config


def remove_project_adapter_module(
    module_name: str,
    config_path: Path | None = None,
) -> UserAdapterConfig:
    config = read_project_adapter_config(config_path)
    config["modules"] = [item for item in config["modules"] if item != module_name]
    for package_name in list(config["packages"]):
        config["packages"][package_name] = [
            item for item in config["packages"][package_name] if item != module_name
        ]
        if not config["packages"][package_name]:
            del config["packages"][package_name]
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
    package_key = normalize_package_id(package_name)
    if not package_key:
        return config
    modules = set(config["packages"].get(package_key, []))
    modules.add(module_name)
    config["packages"][package_key] = sorted(modules)
    write_project_adapter_config(config, config_path)
    return config


def get_project_adapter_package_modules(
    package_name: str,
    config_path: Path | None = None,
) -> list[str]:
    config = read_project_adapter_config(config_path)
    return list(config["packages"].get(normalize_package_id(package_name), []))


def unbind_project_adapter_package(
    package_name: str,
    module_name: str | None = None,
    config_path: Path | None = None,
) -> UserAdapterConfig:
    config = read_project_adapter_config(config_path)
    package_key = normalize_package_id(package_name)
    if not package_key:
        return config
    if module_name is None:
        modules = config["packages"].pop(package_key, [])
        for item in modules:
            config["modules"] = [
                module for module in config["modules"] if module != item
            ]
        write_project_adapter_config(config, config_path)
        return config
    modules = config["packages"].get(package_key, [])
    if not modules:
        return config
    config["packages"][package_key] = [item for item in modules if item != module_name]
    if not config["packages"][package_key]:
        del config["packages"][package_key]
    config["modules"] = [item for item in config["modules"] if item != module_name]
    write_project_adapter_config(config, config_path)
    return config
