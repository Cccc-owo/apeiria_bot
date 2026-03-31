"""Declared config resolution and update validation for plugin settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nonebot.config import Config, Env

from apeiria.app.plugins.config_capabilities import coerce_config_value
from apeiria.infra.config.bot_config import BotConfig
from apeiria.infra.plugin_metadata import configs_from_model
from apeiria.infra.plugin_metadata.resolver import resolve_plugin_declared_config

if TYPE_CHECKING:
    from apeiria.shared.plugin_metadata import RegisterConfig

_CORE_SETTINGS_EXCLUDED_KEYS = {
    "driver",
    "environment",
}


class UnknownPluginSettingFieldError(ValueError):
    """Raised when an update references an undeclared config field."""

    def __init__(self, field_name: str) -> None:
        super().__init__(f"unknown field {field_name}")


@dataclass(frozen=True)
class PluginDeclaredConfig:
    module_name: str
    section: str
    legacy_flatten: bool
    config_source: str
    has_config_model: bool
    configs: list[RegisterConfig]


def get_plugin_declared_configs(module_name: str) -> PluginDeclaredConfig:
    """Resolve a plugin's declared config model and storage section."""
    resolved = resolve_plugin_declared_config(module_name)
    return PluginDeclaredConfig(
        module_name=module_name,
        section=resolved.section,
        legacy_flatten=resolved.legacy_flatten,
        config_source=resolved.source,
        has_config_model=resolved.has_config_model,
        configs=resolved.configs,
    )


def build_core_declared_configs() -> list[RegisterConfig]:
    """Build the editable core config field list."""
    merged: dict[str, RegisterConfig] = {}
    for model in (Env, Config, BotConfig):
        for config in configs_from_model(model):
            if config.key not in _CORE_SETTINGS_EXCLUDED_KEYS:
                merged[config.key] = config
    return list(merged.values())


def validate_and_coerce_updates(
    values: dict[str, object | None],
    clear: list[str],
    configs: list[RegisterConfig],
) -> dict[str, object | None]:
    """Validate update keys and coerce values from transport payloads."""
    allowed_fields = {config.key: config for config in configs}
    updates: dict[str, object | None] = {}
    for key, value in values.items():
        config = allowed_fields.get(key)
        if config is None:
            raise UnknownPluginSettingFieldError(key)
        updates[key] = coerce_config_value(config, value)
    for key in clear:
        if key not in allowed_fields:
            raise UnknownPluginSettingFieldError(key)
        updates[key] = None
    return updates


__all__ = [
    "PluginDeclaredConfig",
    "UnknownPluginSettingFieldError",
    "build_core_declared_configs",
    "get_plugin_declared_configs",
    "validate_and_coerce_updates",
]
