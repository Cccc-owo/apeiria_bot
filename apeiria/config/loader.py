"""Load Apeiria configuration and expand it into the process environment."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from nonebot.log import logger

from apeiria.config.models import AppConfig


def load_config(path: str) -> AppConfig:
    """Load the app configuration from a YAML file.

    Args:
        path: The path to the YAML config file.

    Returns:
        The parsed AppConfig, or a default AppConfig if the file is missing.
    """
    config_path = Path(path)
    if not config_path.exists():
        logger.warning("Config file not found at {}, using defaults", path)
        return AppConfig()

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return AppConfig(**raw)


def to_env_value(value: object) -> str:
    """Convert a Python value into an environment variable string.

    Args:
        value: The value to convert.

    Returns:
        The string form of the value for use as an environment variable.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "1" if value else "0"
    return json.dumps(value)


def _flatten_nested(
    prefix: str,
    obj: dict,
    parent: str = "",
    skipped: list[str] | None = None,
    skip_existing: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Recursively flatten a nested dict into environment variables.

    Args:
        prefix: The uppermost env prefix for the section.
        obj: The nested dict to flatten.
        parent: The accumulated parent key used to build the env name.
        skipped: Optional list to collect env keys that were skipped.
        skip_existing: Whether to skip keys already present in the environment.
    """
    for key, val in obj.items():
        full_key = f"{parent}__{key}" if parent else key
        env_key = f"{prefix}__{full_key}".upper()
        if isinstance(val, dict):
            _flatten_nested(prefix, val, full_key, skipped, skip_existing)
        elif skip_existing and env_key in os.environ:
            if skipped is not None and os.environ[env_key] != to_env_value(val):
                skipped.append(env_key)
        else:
            os.environ[env_key] = to_env_value(val)


def _try_resolve_plugin_contract(name: str):
    """Try to resolve the configuration contract for a plugin name.

    Args:
        name: The plugin module name to resolve.

    Returns:
        The resolved ConfigContract, or None if resolution fails.
    """
    try:
        from apeiria.config.contract import resolve_config_namespace_contract

        return resolve_config_namespace_contract(name)
    except (ImportError, ValueError, TypeError):
        return None


def _try_resolve_adapter_contract(name: str):
    """Try to resolve the configuration contract for an adapter name.

    Args:
        name: The adapter module name to resolve.

    Returns:
        The resolved ConfigContract, or None if resolution fails.
    """
    try:
        from apeiria.plugin.adapter_resolver import resolve_adapter_config

        return resolve_adapter_config(name)
    except (ImportError, ValueError, TypeError):
        return None


_PLUGIN_FIELD_ALIASES: dict[str, dict[str, str]] = {
    "trigger_reply": {"enabled": "trigger_reply__enabled"},
    "friendship": {"enabled": "friendship__enabled"},
}


def _field_alias(contract: Any, plugin_name: str, key: str) -> str | None:
    """Resolve the environment alias for a plugin config field.

    Args:
        contract: The resolved plugin contract, or None.
        plugin_name: The plugin name.
        key: The config field key.

    Returns:
        The field's alias, or None if no alias applies.
    """
    if contract is not None:
        alias = contract.aliases.get(key)
        if alias is not None:
            return alias
    return _PLUGIN_FIELD_ALIASES.get(plugin_name, {}).get(key)


def _inject_plugin_config(
    entries: dict[str, dict],
    set_driver_attr: object | None = None,
    skipped: list[str] | None = None,
    skip_existing: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Inject plugin config entries into the environment.

    Args:
        entries: Mapping of plugin name to its config dict.
        set_driver_attr: Optional driver object to set config attrs on.
        skipped: Optional list to collect env keys that were skipped.
        skip_existing: Whether to skip keys already present in the environment.
    """
    for name, cfg in entries.items():
        if not cfg:
            continue
        contract = _try_resolve_plugin_contract(name)
        for key, val in cfg.items():
            field_name = _field_alias(contract, name, key) or key
            env_key = field_name.upper()
            if skip_existing and env_key in os.environ:
                if skipped is not None and os.environ[env_key] != to_env_value(val):
                    skipped.append(env_key)
            else:
                os.environ[env_key] = to_env_value(val)
            if set_driver_attr is not None:
                setattr(set_driver_attr, field_name, val)


def _inject_section_config(
    entries: dict[str, dict],
    resolve_fn: Callable[[str], Any],
    set_driver_attr: object | None = None,
    skipped: list[str] | None = None,
    skip_existing: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Inject a config section into the environment.

    Args:
        entries: Mapping of section member name to its config dict.
        resolve_fn: Callable that resolves a member's configuration contract.
        set_driver_attr: Optional driver object to set config attrs on.
        skipped: Optional list to collect env keys that were skipped.
        skip_existing: Whether to skip keys already present in the environment.
    """
    for name, cfg in entries.items():
        if not cfg:
            continue
        contract = resolve_fn(name)
        if contract and contract.is_scoped and contract.namespace:
            inner_cfg = cfg.get(contract.namespace, cfg)
            if isinstance(inner_cfg, dict):
                _flatten_nested(
                    contract.namespace.upper(),
                    inner_cfg,
                    skipped=skipped,
                    skip_existing=skip_existing,
                )
                if set_driver_attr is not None:
                    setattr(set_driver_attr, contract.namespace, inner_cfg)
        else:
            for key, val in cfg.items():
                env_key = key.upper()
                if skip_existing and env_key in os.environ:
                    if skipped is not None and os.environ[env_key] != to_env_value(val):
                        skipped.append(env_key)
                else:
                    os.environ[env_key] = to_env_value(val)
                if set_driver_attr is not None:
                    setattr(set_driver_attr, key, val)


def expand_config(app: AppConfig) -> None:
    """Expand the app configuration into the process environment.

    Args:
        app: The app configuration to expand.
    """
    skipped_keys: list[str] = []

    nonebot_fields = {
        name: getattr(app.nonebot, name) for name in app._nonebot_field_names
    }
    for key, value in nonebot_fields.items():
        env_key = key.upper()
        env_value = to_env_value(value)
        if env_key in os.environ:
            if os.environ[env_key] != env_value:
                skipped_keys.append(env_key)
        else:
            os.environ[env_key] = env_value

    _inject_plugin_config(
        app.plugins,
        skipped=skipped_keys,
        skip_existing=True,
    )
    _inject_section_config(
        app.adapters,
        _try_resolve_adapter_contract,
        skipped=skipped_keys,
        skip_existing=True,
    )

    if skipped_keys:
        logger.warning(
            "Skipped {} YAML config key(s) — already set by .env / process env: {}",
            len(skipped_keys),
            ", ".join(sorted(skipped_keys)),
        )

    logger.success("Config expanded from YAML to environment")


def _collect_adapter_entries(*paths: str) -> list[dict]:
    """Collect adapter entries from the given TOML files.

    Args:
        paths: Paths to TOML files that declare adapter config.

    Returns:
        A list of adapter entry dicts, deduplicated by module name.
    """
    import tomllib

    seen_modules: set[str] = set()
    entries: list[dict] = []

    for path in paths:
        toml_path = Path(path)
        if not toml_path.exists():
            continue
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        cfg = raw.get("tool", {}).get("nonebot", {}).get("adapters", {})
        if not isinstance(cfg, dict):
            continue
        for adapter_entries in cfg.values():
            if not isinstance(adapter_entries, list):
                continue
            for entry in adapter_entries:
                if not isinstance(entry, dict):
                    continue
                module_name = entry.get("module_name", "")
                if not module_name or module_name in seen_modules:
                    continue
                seen_modules.add(module_name)
                entries.append(entry)

    return entries


def load_adapters_from_toml(
    *paths: str,
    states: dict[str, dict] | None = None,
) -> int:
    """Load and register adapters declared in the given TOML files.

    Args:
        paths: Paths to TOML files that declare adapter config.
        states: Optional mapping of adapter name to its enabled state.

    Returns:
        The number of adapters registered.
    """
    import importlib

    from nonebot import get_adapters, get_driver

    entries = _collect_adapter_entries(*paths)
    if not entries:
        return 0

    existing = get_adapters()
    driver = get_driver()
    registered = 0

    for entry in entries:
        module_name = entry.get("module_name", "")
        name = entry.get("name", module_name)
        if name in existing:
            continue
        if states is not None:
            state_entry = states.get(name, {})
            if not state_entry.get("enabled", True):
                logger.debug("Skipped disabled adapter: {}", name)
                continue
        try:
            mod = importlib.import_module(module_name)
            adapter_cls = getattr(mod, "Adapter", None)
            if adapter_cls is not None:
                driver.register_adapter(adapter_cls)
                logger.info("Registered adapter: {}", name)
                registered += 1
        except Exception:  # noqa: BLE001
            logger.opt(exception=True).warning(
                "Failed to load adapter: {}", module_name
            )

    return registered


def update_runtime_config(app: AppConfig) -> None:
    """Hot-reload plugin and adapter config into the running driver.

    Args:
        app: The app configuration to apply.
    """
    from nonebot import get_driver

    driver = get_driver()
    config = driver.config

    _inject_plugin_config(app.plugins, set_driver_attr=config)
    _inject_section_config(
        app.adapters, _try_resolve_adapter_contract, set_driver_attr=config
    )

    logger.success("Plugin config hot-reloaded")
