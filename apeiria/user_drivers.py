from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypedDict

from apeiria.package_ids import normalize_package_id

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


class UserDriverConfig(TypedDict):
    builtin: list[str]
    packages: dict[str, list[str]]


logger = logging.getLogger("apeiria.user_drivers")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_config_path() -> Path:
    return _project_root() / "apeiria.drivers.toml"


def _normalize_str_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _load_config(config_path: Path) -> dict[str, Any]:
    if tomllib is None:
        logger.warning(
            "Skip loading apeiria.drivers.toml: tomllib/tomli is unavailable"
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
    if not isinstance(value, dict):
        return {}
    result: dict[str, list[str]] = {}
    for package_name, builtin in value.items():
        if not isinstance(package_name, str) or not package_name.strip():
            continue
        normalized_builtin = sorted(set(_normalize_str_list(builtin)))
        normalized_package = normalize_package_id(package_name)
        if normalized_package and normalized_builtin:
            result[normalized_package] = normalized_builtin
    return result


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
    target.write_text(_dump_config(config), encoding="utf-8")
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
        config["builtin"].append(builtin_name)
        config["builtin"].sort()
        write_project_driver_config(config, config_path)
    return config


def remove_project_driver_builtin(
    builtin_name: str,
    config_path: Path | None = None,
) -> UserDriverConfig:
    config = read_project_driver_config(config_path)
    config["builtin"] = [item for item in config["builtin"] if item != builtin_name]
    for package_name in list(config["packages"]):
        config["packages"][package_name] = [
            item for item in config["packages"][package_name] if item != builtin_name
        ]
        if not config["packages"][package_name]:
            del config["packages"][package_name]
    write_project_driver_config(config, config_path)
    return config


def get_project_driver_kwargs(config_path: Path | None = None) -> dict[str, str]:
    config = read_project_driver_config(config_path)
    if not config["builtin"]:
        return {}
    return {"driver": "+".join(config["builtin"])}


def bind_project_driver_package(
    package_name: str,
    builtin_name: str,
    config_path: Path | None = None,
) -> UserDriverConfig:
    config = add_project_driver_builtin(builtin_name, config_path)
    package_key = normalize_package_id(package_name)
    if not package_key:
        return config
    builtin = set(config["packages"].get(package_key, []))
    builtin.add(builtin_name)
    config["packages"][package_key] = sorted(builtin)
    write_project_driver_config(config, config_path)
    return config


def get_project_driver_package_builtin(
    package_name: str,
    config_path: Path | None = None,
) -> list[str]:
    config = read_project_driver_config(config_path)
    return list(config["packages"].get(normalize_package_id(package_name), []))


def unbind_project_driver_package(
    package_name: str,
    builtin_name: str | None = None,
    config_path: Path | None = None,
) -> UserDriverConfig:
    config = read_project_driver_config(config_path)
    package_key = normalize_package_id(package_name)
    if not package_key:
        return config
    if builtin_name is None:
        builtin = config["packages"].pop(package_key, [])
        for item in builtin:
            config["builtin"] = [name for name in config["builtin"] if name != item]
        write_project_driver_config(config, config_path)
        return config
    builtin = config["packages"].get(package_key, [])
    if not builtin:
        return config
    config["packages"][package_key] = [item for item in builtin if item != builtin_name]
    if not config["packages"][package_key]:
        del config["packages"][package_key]
    config["builtin"] = [item for item in config["builtin"] if item != builtin_name]
    write_project_driver_config(config, config_path)
    return config
