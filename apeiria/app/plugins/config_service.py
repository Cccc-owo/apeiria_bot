"""Plugin configuration read/write services for Web UI and CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from apeiria.app.plugins.registration_service import (
    AdapterConfigState,
    DriverConfigState,
    PluginConfigState,
    plugin_registration_config_service,
)
from apeiria.app.plugins.settings_support import (
    build_core_declared_configs,
    get_plugin_declared_configs,
    validate_and_coerce_updates,
)
from apeiria.app.plugins.settings_view import (
    build_core_setting_fields,
    build_plugin_setting_fields,
)
from apeiria.infra.config import (
    InvalidProjectConfigError,
    project_config_service,
)
from apeiria.infra.plugin_metadata.registry import PluginConfigConflictError

if TYPE_CHECKING:
    from collections.abc import Callable


class PluginSettingsNotConfigurableError(ValueError):
    """Raised when a plugin exists but exposes no editable config model."""


@dataclass(frozen=True)
class PluginSettingFieldState:
    key: str
    type: str
    editor: str
    item_type: str | None
    key_type: str | None
    schema: object | None
    default: object | None
    help: str
    choices: list[object]
    base_value: object | None
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
class PluginRawValidationState:
    valid: bool
    message: str | None = None
    line: int | None = None
    column: int | None = None


class PluginConfigViewService:
    """Build domain-level config views for Web UI and other adapters.

    This service centralizes:
    - current plugin/adapter/driver registration state
    - editable field metadata for config UIs
    - normalized write paths back into project TOML files
    """

    _CORE_SETTINGS_MODULE_NAME = "apeiria.core"

    def get_adapter_config(self) -> AdapterConfigState:
        return plugin_registration_config_service.get_adapter_config()

    def update_adapter_config(self, modules: list[str]) -> AdapterConfigState:
        return plugin_registration_config_service.update_adapter_config(modules)

    def get_driver_config(self) -> DriverConfigState:
        return plugin_registration_config_service.get_driver_config()

    def update_driver_config(self, builtin: list[str]) -> DriverConfigState:
        return plugin_registration_config_service.update_driver_config(builtin)

    def get_plugin_config(self) -> PluginConfigState:
        return plugin_registration_config_service.get_plugin_config()

    def update_plugin_config(
        self,
        modules: list[str],
        dirs: list[str],
    ) -> PluginConfigState:
        return plugin_registration_config_service.update_plugin_config(modules, dirs)

    def get_core_settings(self) -> PluginSettingsState:
        """Return editable NoneBot core settings with source metadata."""
        return PluginSettingsState(
            module_name=self._CORE_SETTINGS_MODULE_NAME,
            section="nonebot",
            legacy_flatten=False,
            config_source="built_in",
            has_config_model=True,
            fields=build_core_setting_fields(),
        )

    def get_core_settings_raw(self) -> PluginRawSettingsState:
        return PluginRawSettingsState(
            module_name=self._CORE_SETTINGS_MODULE_NAME,
            section="nonebot",
            text=project_config_service.read_project_nonebot_section_toml(),
        )

    def update_core_settings(
        self,
        values: dict[str, object | None],
        clear: list[str],
    ) -> PluginSettingsState:
        configs = build_core_declared_configs()
        updates = validate_and_coerce_updates(values, clear, configs)
        project_config_service.write_project_nonebot_config(updates)
        return self.get_core_settings()

    def update_core_settings_raw(self, text: str) -> PluginRawSettingsState:
        project_config_service.write_project_nonebot_section_toml(text)
        return self.get_core_settings_raw()

    def validate_core_settings_raw(self, text: str) -> PluginRawValidationState:
        return self._validate_raw_toml(
            lambda: project_config_service.validate_project_nonebot_section_toml(text)
        )

    def get_plugin_settings(self, module_name: str) -> PluginSettingsState:
        """Return editable settings for one plugin module."""
        declared = get_plugin_declared_configs(module_name)
        return PluginSettingsState(
            module_name=module_name,
            section=declared.section,
            legacy_flatten=declared.legacy_flatten,
            config_source=declared.config_source,
            has_config_model=declared.has_config_model,
            fields=build_plugin_setting_fields(declared),
        )

    def get_plugin_settings_raw(self, module_name: str) -> PluginRawSettingsState:
        declared = get_plugin_declared_configs(module_name)
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
        declared = get_plugin_declared_configs(module_name)
        if not declared.has_config_model:
            raise PluginSettingsNotConfigurableError(module_name)
        updates = validate_and_coerce_updates(values, clear, declared.configs)
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
        declared = get_plugin_declared_configs(module_name)
        project_config_service.write_project_plugin_section_toml(
            declared.section,
            text,
            module_name=module_name,
        )
        return self.get_plugin_settings_raw(module_name)

    def validate_plugin_settings_raw(
        self,
        module_name: str,
        text: str,
    ) -> PluginRawValidationState:
        declared = get_plugin_declared_configs(module_name)
        return self._validate_raw_toml(
            lambda: project_config_service.validate_project_plugin_section_toml(
                declared.section,
                text,
            )
        )

    def _validate_raw_toml(
        self,
        validator: Callable[[], None],
    ) -> PluginRawValidationState:
        try:
            validator()
        except (TypeError, ValueError) as exc:
            return PluginRawValidationState(
                valid=False,
                message=str(exc) or exc.__class__.__name__,
                line=self._extract_error_position(exc, "line"),
                column=self._extract_error_position(exc, "col"),
            )
        return PluginRawValidationState(valid=True)

    def _extract_error_position(self, exc: Exception, attr: str) -> int | None:
        value = getattr(exc, attr, None)
        return value if isinstance(value, int) and value > 0 else None


plugin_config_view_service = PluginConfigViewService()

__all__ = [
    "AdapterConfigState",
    "DriverConfigState",
    "InvalidProjectConfigError",
    "PluginConfigConflictError",
    "PluginConfigState",
    "PluginConfigViewService",
    "PluginRawSettingsState",
    "PluginRawValidationState",
    "PluginSettingFieldState",
    "PluginSettingsNotConfigurableError",
    "PluginSettingsState",
    "plugin_config_view_service",
]
