from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.items

from apeiria.core.configs.registry import build_legacy_nonebot_overrides

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        tomllib = None


logger = logging.getLogger("apeiria.user_config")

_PROJECT_NONEBOT_DEFAULTS: dict[str, Any] = {
    "localstore_use_cwd": True,
}


def _ensure_config_parent(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "apeiria.config.toml"


def _load_config(config_path: Path) -> dict[str, Any]:
    if tomllib is None:
        logger.warning("Skip loading apeiria.config.toml: tomllib/tomli is unavailable")
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


def _normalize_config(data: dict[str, Any]) -> dict[str, Any]:
    nonebot_config = data.get("nonebot")
    if isinstance(nonebot_config, dict):
        return dict(nonebot_config)
    return data


def _read_nonebot_overrides(config_path: Path) -> dict[str, Any]:
    data = _load_config(config_path)
    config = dict(_PROJECT_NONEBOT_DEFAULTS)
    config.update(_normalize_config(data))
    config.update(build_legacy_nonebot_overrides(data))
    return config


def _read_effective_nonebot_config(config_path: Path) -> dict[str, Any]:
    from nonebot.compat import model_dump
    from nonebot.config import Config, Env

    env = Env()
    env_file = f".env.{env.environment}"
    config = Config(
        **_read_nonebot_overrides(config_path),
        _env_file=(".env", env_file),
    )
    return dict(model_dump(config))


def _read_env_nonebot_config() -> dict[str, Any]:
    from nonebot.compat import model_dump
    from nonebot.config import Config, Env

    env = Env()
    env_file = f".env.{env.environment}"
    config = Config(_env_file=(".env", env_file))
    return dict(model_dump(config))


def _plugin_name_candidates(plugin_name: str) -> tuple[str, ...]:
    stripped = plugin_name.strip()
    if not stripped:
        return ()

    candidates = [stripped]
    normalized = stripped.replace("-", "_")
    if normalized not in candidates:
        candidates.append(normalized)
    dashed = stripped.replace("_", "-")
    if dashed not in candidates:
        candidates.append(dashed)
    return tuple(candidates)


def _read_plugin_table(data: dict[str, Any], plugin_name: str) -> dict[str, Any]:
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        return {}

    for candidate in _plugin_name_candidates(plugin_name):
        plugin_config = plugins.get(candidate)
        if isinstance(plugin_config, dict):
            return dict(plugin_config)
    return {}


def default_config_path() -> Path:
    return _default_config_path()


def read_project_config(config_path: Path | None = None) -> dict[str, Any]:
    target = config_path or _default_config_path()
    return _read_effective_nonebot_config(target)


def read_env_config() -> dict[str, Any]:
    return _read_env_nonebot_config()


def get_project_config_kwargs(config_path: Path | None = None) -> dict[str, Any]:
    target = config_path or _default_config_path()
    return _read_nonebot_overrides(target)


def read_raw_project_config(config_path: Path | None = None) -> dict[str, Any]:
    target = config_path or _default_config_path()
    return _load_config(target)


def read_pyproject_nonebot_config(
    config_path: Path | None = None,
) -> dict[str, list[str]]:
    target = config_path or (Path(__file__).resolve().parent.parent / "pyproject.toml")
    data = _load_config(target)
    nonebot_config = data.get("tool", {}).get("nonebot", {})
    if not isinstance(nonebot_config, dict):
        return {"plugins": [], "plugin_dirs": []}

    raw_plugins = nonebot_config.get("plugins", {})
    plugins: list[str]
    if isinstance(raw_plugins, list):
        plugins = [item for item in raw_plugins if isinstance(item, str)]
    elif isinstance(raw_plugins, dict):
        plugins = [
            item
            for item in dict.values(raw_plugins)
            if isinstance(item, list)
            for item in item
            if isinstance(item, str)
        ]
    else:
        plugins = []

    raw_plugin_dirs = nonebot_config.get("plugin_dirs", [])
    plugin_dirs = (
        [item for item in raw_plugin_dirs if isinstance(item, str)]
        if isinstance(raw_plugin_dirs, list)
        else []
    )
    return {"plugins": plugins, "plugin_dirs": plugin_dirs}


def read_project_nonebot_section_config(
    config_path: Path | None = None,
) -> dict[str, Any]:
    target = config_path or _default_config_path()
    nonebot_section = _load_config(target).get("nonebot")
    if isinstance(nonebot_section, dict):
        return dict(nonebot_section)
    return {}


def read_project_plugin_section_names(
    config_path: Path | None = None,
) -> list[str]:
    target = config_path or _default_config_path()
    plugins = _load_config(target).get("plugins")
    if not isinstance(plugins, dict):
        return []
    return [name for name in plugins if isinstance(name, str) and name.strip()]


def read_project_plugin_module_map(
    config_path: Path | None = None,
) -> dict[str, str]:
    target = config_path or _default_config_path()
    mappings = _load_config(target).get("plugin_modules")
    if not isinstance(mappings, dict):
        return {}
    return {
        section: module_name
        for section, module_name in mappings.items()
        if isinstance(section, str)
        and section.strip()
        and isinstance(module_name, str)
        and module_name.strip()
    }


def write_project_plugin_module_map(
    updates: dict[str, str | None],
    config_path: Path | None = None,
) -> Path:
    target = config_path or _default_config_path()
    document = _load_toml_document(target)

    plugin_modules = document.get("plugin_modules")
    if not isinstance(plugin_modules, tomlkit.items.Table):  # type: ignore[attr-defined]
        plugin_modules = tomlkit.table()
        document["plugin_modules"] = plugin_modules

    for section, module_name in updates.items():
        normalized_section = next(iter(_plugin_name_candidates(section)), section)
        if not normalized_section:
            continue
        normalized_module = module_name.strip() if isinstance(module_name, str) else ""
        if normalized_module:
            plugin_modules[normalized_section] = normalized_module
            continue
        if normalized_section in plugin_modules:
            del plugin_modules[normalized_section]

    if len(plugin_modules) == 0 and "plugin_modules" in document:
        del document["plugin_modules"]

    _ensure_config_parent(target)
    target.write_text(tomlkit.dumps(document), encoding="utf-8")
    return target


def read_project_plugin_config(
    plugin_name: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    target = config_path or _default_config_path()
    return _read_plugin_table(_load_config(target), plugin_name)


def _load_toml_document(config_path: Path) -> tomlkit.TOMLDocument:
    if not config_path.is_file():
        return tomlkit.document()
    try:
        return tomlkit.parse(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        logger.warning("Skip loading %s: %s", config_path.name, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Skip loading %s: invalid TOML (%s)", config_path.name, exc)
    return tomlkit.document()


def _dump_toml_value(value: object) -> tomlkit.items.Item:  # type: ignore[attr-defined]
    return tomlkit.item(_normalize_toml_value(value))  # type: ignore[call-overload]


def _normalize_toml_value(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return [_normalize_toml_value(item) for item in sorted(value)]
    if isinstance(value, list | tuple):
        return [_normalize_toml_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_toml_value(item) for key, item in value.items()}
    return value


def _build_table_from_mapping(values: dict[str, Any]) -> tomlkit.items.Table:  # type: ignore[attr-defined]
    table = tomlkit.table()
    for key, value in values.items():
        table[str(key)] = _dump_toml_value(value)
    return table


def _parse_toml_text(text: str) -> tomlkit.TOMLDocument:
    normalized = text.strip()
    if not normalized:
        return tomlkit.document()
    if not normalized.endswith("\n"):
        normalized = f"{normalized}\n"
    return tomlkit.parse(normalized)


def read_project_nonebot_section_toml(
    config_path: Path | None = None,
) -> str:
    target = config_path or _default_config_path()
    section_data = read_project_nonebot_section_config(target)
    document = tomlkit.document()
    document["nonebot"] = _build_table_from_mapping(section_data)
    return tomlkit.dumps(document)


def write_project_nonebot_section_toml(
    text: str,
    config_path: Path | None = None,
) -> Path:
    target = config_path or _default_config_path()
    document = _load_toml_document(target)
    parsed = _parse_toml_text(text)

    if any(key != "nonebot" for key in parsed):
        msg = "raw editor only accepts the [nonebot] section"
        raise ValueError(msg)

    section = parsed.get("nonebot")
    if section is None:
        if "nonebot" in document:
            del document["nonebot"]
    elif not isinstance(section, tomlkit.items.Table):  # type: ignore[attr-defined]
        msg = "raw editor expects a [nonebot] table"
        raise ValueError(msg)
    elif len(section) == 0:
        if "nonebot" in document:
            del document["nonebot"]
    else:
        document["nonebot"] = section

    _ensure_config_parent(target)
    target.write_text(tomlkit.dumps(document), encoding="utf-8")
    return target


def read_project_plugin_section_toml(
    plugin_name: str,
    config_path: Path | None = None,
) -> str:
    target = config_path or _default_config_path()
    section_name = next(iter(_plugin_name_candidates(plugin_name)), plugin_name)
    section_data = read_project_plugin_config(section_name, target)
    document = tomlkit.document()
    plugins = tomlkit.table()
    plugins[section_name] = _build_table_from_mapping(section_data)
    document["plugins"] = plugins
    return tomlkit.dumps(document)


def _validate_plugin_section_toml(
    parsed: dict[str, object],
    section_name: str,
) -> tomlkit.items.Table | None:  # type: ignore[attr-defined]
    if any(key != "plugins" for key in parsed):
        msg = "raw editor only accepts the [plugins.<section>] section"
        raise ValueError(msg)

    plugins_section = parsed.get("plugins")
    if plugins_section is None:
        return None
    if not isinstance(plugins_section, tomlkit.items.Table):  # type: ignore[attr-defined]
        msg = "raw editor expects a [plugins.<section>] table"
        raise TypeError(msg)

    if any(key != section_name for key in plugins_section):
        msg = f"raw editor only accepts the [plugins.{section_name}] section"
        raise ValueError(msg)
    section = plugins_section.get(section_name)
    if section is not None and not isinstance(section, tomlkit.items.Table):  # type: ignore[attr-defined]
        msg = f"raw editor expects [plugins.{section_name}] to be a table"
        raise ValueError(msg)
    return section


def write_project_plugin_section_toml(
    plugin_name: str,
    text: str,
    config_path: Path | None = None,
    *,
    module_name: str | None = None,
) -> Path:
    target = config_path or _default_config_path()
    document = _load_toml_document(target)
    parsed = _parse_toml_text(text)
    section_name = next(iter(_plugin_name_candidates(plugin_name)), plugin_name)

    section = _validate_plugin_section_toml(parsed, section_name)

    plugins = document.get("plugins")
    if not isinstance(plugins, tomlkit.items.Table):  # type: ignore[attr-defined]
        plugins = tomlkit.table()
        document["plugins"] = plugins

    if section is None or len(section) == 0:
        if section_name in plugins:
            del plugins[section_name]
        if len(plugins) == 0 and "plugins" in document:
            del document["plugins"]
        _ensure_config_parent(target)
        target.write_text(tomlkit.dumps(document), encoding="utf-8")
        return write_project_plugin_module_map({section_name: None}, target)

    plugins[section_name] = section
    _ensure_config_parent(target)
    target.write_text(tomlkit.dumps(document), encoding="utf-8")
    if module_name is not None:
        write_project_plugin_module_map({section_name: module_name}, target)
    return target


def write_project_plugin_section_config(
    plugin_name: str,
    values: dict[str, object | None],
    config_path: Path | None = None,
    *,
    module_name: str | None = None,
) -> Path:
    target = config_path or _default_config_path()
    document = _load_toml_document(target)

    plugins = document.get("plugins")
    if not isinstance(plugins, tomlkit.items.Table):  # type: ignore[attr-defined]
        plugins = tomlkit.table()
        document["plugins"] = plugins

    section_name = next(iter(_plugin_name_candidates(plugin_name)), plugin_name)
    section = plugins.get(section_name)
    if not isinstance(section, tomlkit.items.Table):  # type: ignore[attr-defined]
        section = tomlkit.table()
        plugins[section_name] = section

    clear_module_mapping = False

    for key, value in values.items():
        if value is None:
            if key in section:
                del section[key]
            continue
        section[key] = _dump_toml_value(value)

    if len(section) == 0:
        del plugins[section_name]
        clear_module_mapping = True
    if len(plugins) == 0:
        del document["plugins"]

    _ensure_config_parent(target)
    target.write_text(tomlkit.dumps(document), encoding="utf-8")
    if clear_module_mapping:
        write_project_plugin_module_map({section_name: None}, target)
    elif len(section) > 0 and module_name is not None:
        write_project_plugin_module_map({section_name: module_name}, target)
    return target


def write_project_nonebot_config(
    values: dict[str, object | None],
    config_path: Path | None = None,
) -> Path:
    target = config_path or _default_config_path()
    document = _load_toml_document(target)

    section = document.get("nonebot")
    if not isinstance(section, tomlkit.items.Table):  # type: ignore[attr-defined]
        section = tomlkit.table()
        document["nonebot"] = section

    for key, value in values.items():
        if value is None:
            if key in section:
                del section[key]
            continue
        section[key] = _dump_toml_value(value)

    if len(section) == 0:
        del document["nonebot"]

    _ensure_config_parent(target)
    target.write_text(tomlkit.dumps(document), encoding="utf-8")
    return target
