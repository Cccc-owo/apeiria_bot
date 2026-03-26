"""Plugin configuration read/write services for Web UI and CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Literal, overload

import nonebot
from nonebot.config import Config, Env

from apeiria.config import (
    InvalidProjectConfigError,
    adapter_config_service,
    driver_config_service,
    plugin_config_service,
    project_config_service,
)
from apeiria.core.configs import configs_from_model
from apeiria.core.configs.capabilities import (
    coerce_config_value,
    format_type_name,
    get_field_capability,
    normalize_choices_for_response,
    normalize_value_for_response,
)
from apeiria.core.configs.config import BotConfig
from apeiria.core.configs.plugin_config_resolver import resolve_plugin_declared_config
from apeiria.core.configs.registry import (
    PluginConfigConflictError,
    get_registered_plugin_config,
)

if TYPE_CHECKING:
    from apeiria.config.adapters import AdapterConfig
    from apeiria.config.drivers import DriverConfig
    from apeiria.config.plugins import PluginConfig
    from apeiria.core.configs.models import RegisterConfig

_CORE_SETTINGS_EXCLUDED_KEYS = {
    "driver",
    "environment",
}


class PluginSettingsNotConfigurableError(ValueError):
    """Raised when a plugin exists but exposes no editable config model."""


class UnknownPluginSettingFieldError(ValueError):
    """Raised when an update references an undeclared config field."""

    def __init__(self, field_name: str) -> None:
        super().__init__(f"unknown field {field_name}")


@dataclass(frozen=True)
class FieldValueState:
    current_value: object | None
    local_value: object | None
    value_source: str
    global_key: str | None = None
    has_local_override: bool = False


@dataclass(frozen=True)
class PluginDeclaredConfig:
    module_name: str
    section: str
    legacy_flatten: bool
    config_source: str
    has_config_model: bool
    configs: list[RegisterConfig]


@dataclass(frozen=True)
class PluginConfigModuleStatus:
    name: str
    is_loaded: bool
    is_importable: bool


@dataclass(frozen=True)
class PluginConfigDirStatus:
    path: str
    exists: bool
    is_loaded: bool


@dataclass(frozen=True)
class AdapterConfigStatus:
    name: str
    is_loaded: bool
    is_importable: bool


@dataclass(frozen=True)
class DriverConfigStatus:
    name: str
    is_active: bool


@dataclass(frozen=True)
class PluginSettingFieldState:
    key: str
    type: str
    editor: str
    item_type: str | None
    key_type: str | None
    default: object | None
    help: str
    choices: list[object]
    current_value: object | None
    local_value: object | None
    value_source: str
    global_key: str | None
    has_local_override: bool
    allows_null: bool
    editable: bool
    type_category: str


@dataclass(frozen=True)
class PluginSettingsState:
    module_name: str
    section: str
    legacy_flatten: bool
    config_source: str
    has_config_model: bool
    fields: list[PluginSettingFieldState]


@dataclass(frozen=True)
class PluginRawSettingsState:
    module_name: str
    section: str
    text: str


@dataclass(frozen=True)
class PluginConfigState:
    modules: list[PluginConfigModuleStatus]
    dirs: list[PluginConfigDirStatus]


@dataclass(frozen=True)
class AdapterConfigState:
    modules: list[AdapterConfigStatus]


@dataclass(frozen=True)
class DriverConfigState:
    builtin: list[DriverConfigStatus]


@dataclass(frozen=True)
class _PluginFieldContext:
    plugin_config: dict[str, object]
    effective_global_config: dict[str, object]
    env_config: dict[str, object]
    nonebot_section: dict[str, object]
    legacy_flatten: bool
    key_map: dict[str, str]


class PluginConfigViewService:
    """Build domain-level config views for Web UI and other adapters.

    This service centralizes:
    - current plugin/adapter/driver registration state
    - editable field metadata for config UIs
    - normalized write paths back into project TOML files
    """

    def get_adapter_config(self) -> AdapterConfigState:
        config = adapter_config_service.read_project_adapter_config()
        return AdapterConfigState(
            modules=self._build_adapter_config_items(config["modules"]),
        )

    def update_adapter_config(self, modules: list[str]) -> AdapterConfigState:
        current = adapter_config_service.read_project_adapter_config()
        config = self._update_config_with_packages(current, modules, "modules")
        adapter_config_service.write_project_adapter_config(config)
        return AdapterConfigState(
            modules=self._build_adapter_config_items(config["modules"]),
        )

    def get_driver_config(self) -> DriverConfigState:
        config = driver_config_service.read_project_driver_config()
        return DriverConfigState(
            builtin=self._build_driver_config_items(config["builtin"]),
        )

    def update_driver_config(self, builtin: list[str]) -> DriverConfigState:
        current = driver_config_service.read_project_driver_config()
        config = self._update_config_with_packages(current, builtin, "builtin")
        driver_config_service.write_project_driver_config(config)
        return DriverConfigState(
            builtin=self._build_driver_config_items(config["builtin"]),
        )

    def get_plugin_config(self) -> PluginConfigState:
        config = plugin_config_service.read_project_plugin_config()
        return PluginConfigState(
            modules=self._build_module_config_items(config["modules"]),
            dirs=self._build_dir_config_items(config["dirs"]),
        )

    def update_plugin_config(
        self,
        modules: list[str],
        dirs: list[str],
    ) -> PluginConfigState:
        current = plugin_config_service.read_project_plugin_config()
        normalized_modules = self._normalize_entries(modules)
        normalized_dirs = self._normalize_entries(dirs)
        config: PluginConfig = {
            "modules": normalized_modules,
            "dirs": normalized_dirs,
            "packages": {
                package_name: [
                    item for item in package_modules if item in normalized_modules
                ]
                for package_name, package_modules in current["packages"].items()
            },
        }
        config["packages"] = {
            package_name: package_modules
            for package_name, package_modules in config["packages"].items()
            if package_modules
        }
        plugin_config_service.write_project_plugin_config(config)
        return PluginConfigState(
            modules=self._build_module_config_items(config["modules"]),
            dirs=self._build_dir_config_items(config["dirs"]),
        )

    def get_core_settings(self) -> PluginSettingsState:
        """Return editable NoneBot core settings with source metadata."""
        return PluginSettingsState(
            module_name="apeiria.core",
            section="nonebot",
            legacy_flatten=False,
            config_source="built_in",
            has_config_model=True,
            fields=self._build_core_setting_fields(),
        )

    def get_core_settings_raw(self) -> PluginRawSettingsState:
        return PluginRawSettingsState(
            module_name="apeiria.core",
            section="nonebot",
            text=project_config_service.read_project_nonebot_section_toml(),
        )

    def update_core_settings(
        self,
        values: dict[str, object | None],
        clear: list[str],
    ) -> PluginSettingsState:
        configs = self._build_core_declared_configs()
        updates = self._validate_and_coerce_updates(values, clear, configs)
        project_config_service.write_project_nonebot_config(updates)
        return self.get_core_settings()

    def update_core_settings_raw(self, text: str) -> PluginRawSettingsState:
        project_config_service.write_project_nonebot_section_toml(text)
        return self.get_core_settings_raw()

    def get_plugin_settings(self, module_name: str) -> PluginSettingsState:
        """Return editable settings for one plugin module."""
        declared = self._get_plugin_declared_configs(module_name)
        return PluginSettingsState(
            module_name=module_name,
            section=declared.section,
            legacy_flatten=declared.legacy_flatten,
            config_source=declared.config_source,
            has_config_model=declared.has_config_model,
            fields=self._build_plugin_setting_fields(declared),
        )

    def get_plugin_settings_raw(self, module_name: str) -> PluginRawSettingsState:
        declared = self._get_plugin_declared_configs(module_name)
        return PluginRawSettingsState(
            module_name=module_name,
            section=declared.section,
            text=project_config_service.read_project_plugin_section_toml(
                declared.section
            ),
        )

    def update_plugin_settings(
        self,
        module_name: str,
        values: dict[str, object | None],
        clear: list[str],
    ) -> PluginSettingsState:
        """Validate and persist structured plugin setting updates."""
        declared = self._get_plugin_declared_configs(module_name)
        if not declared.has_config_model:
            raise PluginSettingsNotConfigurableError(module_name)
        updates = self._validate_and_coerce_updates(values, clear, declared.configs)
        project_config_service.write_project_plugin_section_config(
            declared.section,
            updates,
            module_name=module_name,
        )
        return self.get_plugin_settings(module_name)

    def update_plugin_settings_raw(
        self,
        module_name: str,
        text: str,
    ) -> PluginRawSettingsState:
        """Persist raw TOML for a single plugin config section."""
        declared = self._get_plugin_declared_configs(module_name)
        project_config_service.write_project_plugin_section_toml(
            declared.section,
            text,
            module_name=module_name,
        )
        return self.get_plugin_settings_raw(module_name)

    def _loaded_plugin_modules(self) -> set[str]:
        return {plugin.module_name for plugin in nonebot.get_loaded_plugins()}

    def _loaded_adapter_modules(self) -> set[str]:
        return {
            self._normalize_adapter_module_name(adapter.__module__)
            for adapter in nonebot.get_adapters().values()
        }

    def _normalize_adapter_module_name(self, module_name: str) -> str:
        if module_name.endswith(".adapter"):
            return module_name[: -len(".adapter")]
        return module_name

    def _loaded_plugin_paths(self) -> list[Path]:
        result: list[Path] = []
        for plugin in nonebot.get_loaded_plugins():
            module = getattr(plugin, "module", None)
            module_file = getattr(module, "__file__", None)
            if not module_file:
                continue
            try:
                result.append(Path(module_file).resolve())
            except OSError:
                continue
        return result

    def _build_module_config_items(
        self,
        modules: list[str],
    ) -> list[PluginConfigModuleStatus]:
        loaded_modules = self._loaded_plugin_modules()
        items: list[PluginConfigModuleStatus] = []
        for module_name in modules:
            try:
                is_importable = find_spec(module_name) is not None
            except (ImportError, ModuleNotFoundError, ValueError):
                is_importable = False
            items.append(
                PluginConfigModuleStatus(
                    name=module_name,
                    is_loaded=module_name in loaded_modules,
                    is_importable=is_importable,
                )
            )
        return items

    def _build_dir_config_items(
        self,
        dirs: list[str],
    ) -> list[PluginConfigDirStatus]:
        config_root = plugin_config_service.default_config_path().parent.resolve()
        loaded_paths = self._loaded_plugin_paths()
        items: list[PluginConfigDirStatus] = []
        for raw_dir in dirs:
            directory = Path(raw_dir).expanduser()
            if not directory.is_absolute():
                directory = config_root / directory
            try:
                resolved = directory.resolve()
            except OSError:
                resolved = directory

            exists = resolved.is_dir()
            is_loaded = (
                any(
                    resolved == path.parent or resolved in path.parents
                    for path in loaded_paths
                )
                if exists
                else False
            )
            items.append(
                PluginConfigDirStatus(
                    path=raw_dir,
                    exists=exists,
                    is_loaded=is_loaded,
                )
            )
        return items

    def _build_adapter_config_items(
        self,
        modules: list[str],
    ) -> list[AdapterConfigStatus]:
        loaded_modules = self._loaded_adapter_modules()
        items: list[AdapterConfigStatus] = []
        for module_name in modules:
            try:
                is_importable = find_spec(module_name) is not None
            except (ImportError, ModuleNotFoundError, ValueError):
                is_importable = False
            items.append(
                AdapterConfigStatus(
                    name=module_name,
                    is_loaded=module_name in loaded_modules,
                    is_importable=is_importable,
                )
            )
        return items

    def _active_driver_builtin(self) -> list[str]:
        configured = getattr(nonebot.get_driver().config, "driver", None)
        if isinstance(configured, str) and configured:
            return sorted(item for item in configured.split("+") if item)
        return []

    def _build_driver_config_items(
        self,
        builtin: list[str],
    ) -> list[DriverConfigStatus]:
        active_builtin = set(self._active_driver_builtin())
        return [
            DriverConfigStatus(name=item, is_active=item in active_builtin)
            for item in builtin
        ]

    def _normalize_entries(self, values: list[str]) -> list[str]:
        return sorted({item.strip() for item in values if item.strip()})

    def _get_plugin_declared_configs(self, module_name: str) -> PluginDeclaredConfig:
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

    def _build_plugin_field_state(
        self,
        config: RegisterConfig,
        ctx: _PluginFieldContext,
    ) -> FieldValueState:
        current_value: object | None = config.default
        local_value: object | None = None
        value_source = "default"
        global_key = (
            ctx.key_map.get(config.key, config.key) if ctx.legacy_flatten else None
        )

        if ctx.legacy_flatten and global_key:
            if global_key in ctx.nonebot_section:
                current_value = ctx.nonebot_section[global_key]
                value_source = "legacy_global"
            elif global_key in ctx.env_config:
                current_value = ctx.env_config[global_key]
                value_source = "env"
            elif global_key in ctx.effective_global_config:
                current_value = ctx.effective_global_config[global_key]
                value_source = "legacy_global"
        if config.key in ctx.plugin_config:
            local_value = ctx.plugin_config[config.key]
            current_value = ctx.plugin_config[config.key]
            value_source = "plugin_section"

        return FieldValueState(
            current_value=current_value,
            local_value=local_value,
            value_source=value_source,
            global_key=global_key,
            has_local_override=config.key in ctx.plugin_config,
        )

    def _build_core_field_state(
        self,
        config: RegisterConfig,
        env_config: dict[str, object],
        effective_config: dict[str, object],
        section_config: dict[str, object],
    ) -> FieldValueState:
        current_value: object | None = config.default
        local_value: object | None = None
        value_source = "default"

        if config.key in env_config and env_config[config.key] != config.default:
            current_value = env_config[config.key]
            value_source = "env"
        if config.key in section_config:
            local_value = section_config[config.key]
            current_value = section_config[config.key]
            value_source = "plugin_section"
        elif (
            config.key in effective_config
            and effective_config[config.key] != config.default
        ):
            current_value = effective_config[config.key]
            value_source = "env"

        return FieldValueState(
            current_value=current_value,
            local_value=local_value,
            value_source=value_source,
            has_local_override=config.key in section_config,
        )

    def _build_plugin_setting_fields(
        self,
        declared: PluginDeclaredConfig,
    ) -> list[PluginSettingFieldState]:
        """Combine config declarations with current effective values."""
        registration = get_registered_plugin_config(declared.module_name)
        ctx = _PluginFieldContext(
            plugin_config=project_config_service.read_project_plugin_config(
                declared.section
            ),
            effective_global_config=project_config_service.read_project_config(),
            env_config=project_config_service.read_env_config(),
            nonebot_section=project_config_service.read_project_nonebot_section_config(),
            legacy_flatten=declared.legacy_flatten,
            key_map=registration.key_map if registration is not None else {},
        )
        return [
            self._build_setting_field_item(
                config,
                self._build_plugin_field_state(config, ctx),
            )
            for config in declared.configs
        ]

    def _build_core_setting_fields(self) -> list[PluginSettingFieldState]:
        effective_config = project_config_service.read_project_config()
        env_config = project_config_service.read_env_config()
        section_config = project_config_service.read_project_nonebot_section_config()
        return [
            self._build_setting_field_item(
                config,
                self._build_core_field_state(
                    config,
                    env_config,
                    effective_config,
                    section_config,
                ),
            )
            for config in self._build_core_declared_configs()
        ]

    def _build_core_declared_configs(self) -> list[RegisterConfig]:
        merged: dict[str, RegisterConfig] = {}
        for model in (Env, Config, BotConfig):
            for config in configs_from_model(model):
                if config.key not in _CORE_SETTINGS_EXCLUDED_KEYS:
                    merged[config.key] = config
        return list(merged.values())

    def _build_setting_field_item(
        self,
        config: RegisterConfig,
        state: FieldValueState,
    ) -> PluginSettingFieldState:
        capability = get_field_capability(config)
        return PluginSettingFieldState(
            key=config.key,
            type=format_type_name(config.type) or "unknown",
            editor=capability.editor,
            item_type=format_type_name(config.item_type),
            key_type=format_type_name(config.key_type),
            default=normalize_value_for_response(config, config.default),
            help=config.help,
            choices=normalize_choices_for_response(list(config.choices)),
            current_value=normalize_value_for_response(config, state.current_value),
            local_value=normalize_value_for_response(config, state.local_value),
            value_source=state.value_source,
            global_key=state.global_key,
            has_local_override=state.has_local_override,
            allows_null=config.allows_null,
            editable=capability.editable,
            type_category=capability.category,
        )

    def _validate_and_coerce_updates(
        self,
        values: dict[str, object | None],
        clear: list[str],
        configs: list[RegisterConfig],
    ) -> dict[str, object | None]:
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

    @overload
    def _update_config_with_packages(
        self,
        current: AdapterConfig,
        entries: list[str],
        key: Literal["modules"],
    ) -> AdapterConfig: ...

    @overload
    def _update_config_with_packages(
        self,
        current: DriverConfig,
        entries: list[str],
        key: Literal["builtin"],
    ) -> DriverConfig: ...

    def _update_config_with_packages(
        self,
        current: AdapterConfig | DriverConfig,
        entries: list[str],
        key: Literal["modules", "builtin"],
    ) -> AdapterConfig | DriverConfig:
        normalized = self._normalize_entries(entries)
        packages = {
            package_name: [item for item in items if item in normalized]
            for package_name, items in current["packages"].items()
        }
        packages = {
            package_name: items
            for package_name, items in packages.items()
            if items
        }
        if key == "modules":
            return {
                "modules": normalized,
                "packages": packages,
            }
        return {
            "builtin": normalized,
            "packages": packages,
        }


plugin_config_view_service = PluginConfigViewService()

__all__ = [
    "AdapterConfigState",
    "AdapterConfigStatus",
    "DriverConfigState",
    "DriverConfigStatus",
    "InvalidProjectConfigError",
    "PluginConfigConflictError",
    "PluginConfigDirStatus",
    "PluginConfigModuleStatus",
    "PluginConfigState",
    "PluginConfigViewService",
    "PluginDeclaredConfig",
    "PluginRawSettingsState",
    "PluginSettingFieldState",
    "PluginSettingsNotConfigurableError",
    "PluginSettingsState",
    "UnknownPluginSettingFieldError",
    "plugin_config_view_service",
]
