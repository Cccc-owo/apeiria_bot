"""Plugin routes — list and manage plugins."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import nonebot
from fastapi import APIRouter, Depends, HTTPException
from nonebot.config import Config, Env

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
from apeiria.core.configs.registry import get_registered_plugin_config
from apeiria.core.i18n import t
from apeiria.core.utils.helpers import (
    get_plugin_name,
    get_plugin_protection_reason,
    get_plugin_source,
)
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import (
    AdapterConfigItem,
    AdapterConfigRequest,
    AdapterConfigResponse,
    DriverConfigItem,
    DriverConfigRequest,
    DriverConfigResponse,
    PluginConfigDirItem,
    PluginConfigModuleItem,
    PluginConfigRequest,
    PluginConfigResponse,
    PluginItem,
    PluginRawSettingsResponse,
    PluginSettingFieldItem,
    PluginSettingsRawUpdateRequest,
    PluginSettingsResponse,
    PluginSettingsUpdateRequest,
)
from apeiria.user_adapters import (
    read_project_adapter_config,
    write_project_adapter_config,
)
from apeiria.user_config import (
    read_env_config,
    read_project_config,
    read_project_nonebot_section_config,
    read_project_nonebot_section_toml,
    read_project_plugin_section_toml,
    write_project_nonebot_config,
    write_project_nonebot_section_toml,
    write_project_plugin_section_config,
    write_project_plugin_section_toml,
)
from apeiria.user_config import (
    read_project_plugin_config as read_project_plugin_section_config,
)
from apeiria.user_drivers import (
    read_project_driver_config,
    write_project_driver_config,
)
from apeiria.user_plugins import (
    default_config_path,
    read_project_plugin_config,
    write_project_plugin_config,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from apeiria.core.configs.models import RegisterConfig

router = APIRouter()

_CORE_SETTINGS_EXCLUDED_KEYS = {
    "driver",
    "environment",
}


def _loaded_plugin_modules() -> set[str]:
    return {plugin.module_name for plugin in nonebot.get_loaded_plugins()}


def _loaded_adapter_modules() -> set[str]:
    return {
        _normalize_adapter_module_name(adapter.__module__)
        for adapter in nonebot.get_adapters().values()
    }


def _normalize_adapter_module_name(module_name: str) -> str:
    if module_name.endswith(".adapter"):
        return module_name[: -len(".adapter")]
    return module_name


def _loaded_plugin_paths() -> list[Path]:
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


def _build_module_config_items(modules: list[str]) -> list[PluginConfigModuleItem]:
    loaded_modules = _loaded_plugin_modules()
    items: list[PluginConfigModuleItem] = []
    for module_name in modules:
        is_loaded = module_name in loaded_modules
        try:
            is_importable = find_spec(module_name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            is_importable = False
        items.append(
            PluginConfigModuleItem(
                name=module_name,
                is_loaded=is_loaded,
                is_importable=is_importable,
            )
        )
    return items


def _build_dir_config_items(dirs: list[str]) -> list[PluginConfigDirItem]:
    config_root = default_config_path().parent.resolve()
    loaded_paths = _loaded_plugin_paths()
    items: list[PluginConfigDirItem] = []
    for raw_dir in dirs:
        directory = Path(raw_dir).expanduser()
        if not directory.is_absolute():
            directory = config_root / directory
        try:
            resolved = directory.resolve()
        except OSError:
            resolved = directory

        exists = resolved.is_dir()
        is_loaded = any(
            resolved == path.parent or resolved in path.parents
            for path in loaded_paths
        ) if exists else False
        items.append(
            PluginConfigDirItem(
                path=raw_dir,
                exists=exists,
                is_loaded=is_loaded,
            )
        )
    return items


def _build_adapter_config_items(modules: list[str]) -> list[AdapterConfigItem]:
    loaded_modules = _loaded_adapter_modules()
    items: list[AdapterConfigItem] = []
    for module_name in modules:
        try:
            is_importable = find_spec(module_name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            is_importable = False
        items.append(
            AdapterConfigItem(
                name=module_name,
                is_loaded=module_name in loaded_modules,
                is_importable=is_importable,
            )
        )
    return items


def _active_driver_builtin() -> list[str]:
    configured = getattr(nonebot.get_driver().config, "driver", None)
    if isinstance(configured, str) and configured:
        return sorted(item for item in configured.split("+") if item)
    return []


def _build_driver_config_items(builtin: list[str]) -> list[DriverConfigItem]:
    active_builtin = set(_active_driver_builtin())
    return [
        DriverConfigItem(name=item, is_active=item in active_builtin)
        for item in builtin
    ]


def _normalize_entries(values: list[str]) -> list[str]:
    return sorted({item.strip() for item in values if item.strip()})


def _get_plugin_declared_configs(
    module_name: str,
) -> tuple[str, bool, str, bool, list[RegisterConfig]]:
    resolved = resolve_plugin_declared_config(module_name)
    return (
        resolved.section,
        resolved.legacy_flatten,
        resolved.source,
        resolved.has_config_model,
        resolved.configs,
    )


@dataclass(frozen=True)
class FieldValueState:
    current_value: object | None
    local_value: object | None
    value_source: str
    global_key: str | None = None
    has_local_override: bool = False


@dataclass(frozen=True)
class _PluginFieldContext:
    plugin_config: dict[str, object]
    effective_global_config: dict[str, object]
    env_config: dict[str, object]
    nonebot_section: dict[str, object]
    legacy_flatten: bool
    key_map: dict[str, str]


def _build_plugin_field_state(
    config: RegisterConfig,
    ctx: _PluginFieldContext,
) -> FieldValueState:
    current_value: object | None = config.default
    local_value: object | None = None
    value_source = "default"
    global_key = (
        ctx.key_map.get(config.key, config.key)
        if ctx.legacy_flatten
        else None
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
    module_name: str,
    section: str,
    *,
    legacy_flatten: bool,
    configs: list[RegisterConfig],
) -> list[PluginSettingFieldItem]:
    registration = get_registered_plugin_config(module_name)
    ctx = _PluginFieldContext(
        plugin_config=read_project_plugin_section_config(section),
        effective_global_config=read_project_config(),
        env_config=read_env_config(),
        nonebot_section=read_project_nonebot_section_config(),
        legacy_flatten=legacy_flatten,
        key_map=registration.key_map if registration is not None else {},
    )
    return [
        _build_setting_field_item(
            config,
            _build_plugin_field_state(config, ctx),
        )
        for config in configs
    ]


def _build_core_setting_fields() -> list[PluginSettingFieldItem]:
    effective_config = read_project_config()
    env_config = read_env_config()
    section_config = read_project_nonebot_section_config()
    return [
        _build_setting_field_item(
            config,
            _build_core_field_state(
                config,
                env_config,
                effective_config,
                section_config,
            ),
        )
        for config in _build_core_declared_configs()
    ]


def _build_core_declared_configs() -> list[RegisterConfig]:
    merged: dict[str, RegisterConfig] = {}
    for model in (Env, Config, BotConfig):
        for config in configs_from_model(model):
            if config.key not in _CORE_SETTINGS_EXCLUDED_KEYS:
                merged[config.key] = config
    return list(merged.values())


def _build_setting_field_item(
    config: RegisterConfig,
    state: FieldValueState,
) -> PluginSettingFieldItem:
    capability = get_field_capability(config)
    return PluginSettingFieldItem(
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
    payload: PluginSettingsUpdateRequest,
    configs: list[RegisterConfig],
) -> dict[str, object | None]:
    allowed_fields = {config.key: config for config in configs}
    updates: dict[str, object | None] = {}
    for key, value in payload.values.items():
        config = allowed_fields.get(key)
        if config is None:
            raise HTTPException(status_code=400, detail=f"unknown field {key}")
        updates[key] = coerce_config_value(config, value)
    for key in payload.clear:
        if key not in allowed_fields:
            raise HTTPException(status_code=400, detail=f"unknown field {key}")
        updates[key] = None
    return updates


def _update_config_with_packages(
    current: Mapping[str, Any],
    entries: list[str],
    key: str,
) -> dict[str, Any]:
    normalized = _normalize_entries(entries)
    config: dict[str, Any] = {
        key: normalized,
        "packages": {
            package_name: [item for item in items if item in normalized]
            for package_name, items in current["packages"].items()
        },
    }
    config["packages"] = {
        package_name: items
        for package_name, items in config["packages"].items()
        if items
    }
    return config


@router.get("/adapters/config", response_model=AdapterConfigResponse)
async def get_adapter_config(
    _: Annotated[Any, Depends(require_auth)],
) -> AdapterConfigResponse:
    config = read_project_adapter_config()
    return AdapterConfigResponse(
        modules=_build_adapter_config_items(config["modules"]),
    )


@router.patch("/adapters/config", response_model=AdapterConfigResponse)
async def update_adapter_config(
    payload: AdapterConfigRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> AdapterConfigResponse:
    current = read_project_adapter_config()
    config = _update_config_with_packages(current, payload.modules, "modules")
    write_project_adapter_config(config)  # type: ignore[arg-type]
    return AdapterConfigResponse(
        modules=_build_adapter_config_items(config["modules"]),
    )


@router.get("/drivers/config", response_model=DriverConfigResponse)
async def get_driver_config(
    _: Annotated[Any, Depends(require_auth)],
) -> DriverConfigResponse:
    config = read_project_driver_config()
    return DriverConfigResponse(
        builtin=_build_driver_config_items(config["builtin"]),
    )


@router.patch("/drivers/config", response_model=DriverConfigResponse)
async def update_driver_config(
    payload: DriverConfigRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> DriverConfigResponse:
    current = read_project_driver_config()
    config = _update_config_with_packages(current, payload.builtin, "builtin")
    write_project_driver_config(config)  # type: ignore[arg-type]
    return DriverConfigResponse(
        builtin=_build_driver_config_items(config["builtin"]),
    )


@router.get("/config", response_model=PluginConfigResponse)
async def get_plugin_config(
    _: Annotated[Any, Depends(require_auth)],
) -> PluginConfigResponse:
    config = read_project_plugin_config()
    return PluginConfigResponse(
        modules=_build_module_config_items(config["modules"]),
        dirs=_build_dir_config_items(config["dirs"]),
    )


@router.get("/core/settings", response_model=PluginSettingsResponse)
async def get_core_settings(
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    return PluginSettingsResponse(
        module_name="apeiria.core",
        section="nonebot",
        legacy_flatten=False,
        config_source="built_in",
        has_config_model=True,
        fields=_build_core_setting_fields(),
    )


@router.get("/core/settings/raw", response_model=PluginRawSettingsResponse)
async def get_core_settings_raw(
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    return PluginRawSettingsResponse(
        module_name="apeiria.core",
        section="nonebot",
        text=read_project_nonebot_section_toml(),
    )


@router.get("/{module_name}/settings", response_model=PluginSettingsResponse)
async def get_plugin_settings(
    module_name: str,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    section, legacy_flatten, config_source, has_config_model, configs = (
        _get_plugin_declared_configs(module_name)
    )
    return PluginSettingsResponse(
        module_name=module_name,
        section=section,
        legacy_flatten=legacy_flatten,
        config_source=config_source,
        has_config_model=has_config_model,
        fields=_build_plugin_setting_fields(
            module_name,
            section,
            legacy_flatten=legacy_flatten,
            configs=configs,
        ),
    )


@router.get("/{module_name}/settings/raw", response_model=PluginRawSettingsResponse)
async def get_plugin_settings_raw(
    module_name: str,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    section, _, _, _, _ = _get_plugin_declared_configs(module_name)
    return PluginRawSettingsResponse(
        module_name=module_name,
        section=section,
        text=read_project_plugin_section_toml(section),
    )


@router.patch("/core/settings", response_model=PluginSettingsResponse)
async def update_core_settings(
    payload: PluginSettingsUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    configs = _build_core_declared_configs()
    updates = _validate_and_coerce_updates(payload, configs)

    write_project_nonebot_config(updates)
    return PluginSettingsResponse(
        module_name="apeiria.core",
        section="nonebot",
        legacy_flatten=False,
        config_source="built_in",
        has_config_model=True,
        fields=_build_core_setting_fields(),
    )


@router.patch("/core/settings/raw", response_model=PluginRawSettingsResponse)
async def update_core_settings_raw(
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    try:
        write_project_nonebot_section_toml(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PluginRawSettingsResponse(
        module_name="apeiria.core",
        section="nonebot",
        text=read_project_nonebot_section_toml(),
    )


@router.patch("/{module_name}/settings", response_model=PluginSettingsResponse)
async def update_plugin_settings(
    module_name: str,
    payload: PluginSettingsUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    section, legacy_flatten, config_source, has_config_model, configs = (
        _get_plugin_declared_configs(module_name)
    )
    if not has_config_model:
        raise HTTPException(status_code=404, detail="plugin has no configurable fields")

    updates = _validate_and_coerce_updates(payload, configs)

    write_project_plugin_section_config(
        section,
        updates,
        module_name=module_name,
    )
    return PluginSettingsResponse(
        module_name=module_name,
        section=section,
        legacy_flatten=legacy_flatten,
        config_source=config_source,
        has_config_model=has_config_model,
        fields=_build_plugin_setting_fields(
            module_name,
            section,
            legacy_flatten=legacy_flatten,
            configs=configs,
        ),
    )


@router.patch("/{module_name}/settings/raw", response_model=PluginRawSettingsResponse)
async def update_plugin_settings_raw(
    module_name: str,
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    section, _, _, _, _ = _get_plugin_declared_configs(module_name)
    try:
        write_project_plugin_section_toml(
            section,
            payload.text,
            module_name=module_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PluginRawSettingsResponse(
        module_name=module_name,
        section=section,
        text=read_project_plugin_section_toml(section),
    )


@router.patch("/config", response_model=PluginConfigResponse)
async def update_plugin_config(
    payload: PluginConfigRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginConfigResponse:
    current = read_project_plugin_config()
    normalized_modules = _normalize_entries(payload.modules)
    normalized_dirs = _normalize_entries(payload.dirs)
    config = {
        "modules": normalized_modules,
        "dirs": normalized_dirs,
        "packages": {
            package_name: [item for item in modules if item in normalized_modules]
            for package_name, modules in current["packages"].items()
        },
    }
    config["packages"] = {
        package_name: modules
        for package_name, modules in config["packages"].items()
        if modules
    }
    write_project_plugin_config(config)  # type: ignore[arg-type]
    return PluginConfigResponse(
        modules=_build_module_config_items(config["modules"]),
        dirs=_build_dir_config_items(config["dirs"]),
    )


@router.get("/", response_model=list[PluginItem])
async def list_plugins(_: Annotated[Any, Depends(require_auth)]) -> list[PluginItem]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.plugin_info import PluginInfo

    enabled_map: dict[str, bool] = {}
    async with get_session() as session:
        result = await session.execute(
            select(PluginInfo.module_name, PluginInfo.is_global_enabled)
        )
        enabled_map = {  # pyright: ignore[reportAssignmentType]
            row[0]: row[1] for row in result.all()
        }

    plugins: list[PluginItem] = []
    for plugin in nonebot.get_loaded_plugins():
        meta = plugin.metadata
        protected_reason = get_plugin_protection_reason(plugin.module_name)
        plugins.append(
            PluginItem(
                module_name=plugin.module_name,
                name=get_plugin_name(plugin),
                description=meta.description if meta else None,
                source=get_plugin_source(plugin),
                is_global_enabled=enabled_map.get(plugin.module_name, True),
                is_protected=protected_reason is not None,
                protected_reason=protected_reason,
            )
        )
    return plugins


@router.patch("/{module_name}")
async def update_plugin(
    module_name: str,
    _: Annotated[Any, Depends(require_auth)],
    *,
    enabled: bool = True,
) -> dict[str, str]:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.plugin_info import PluginInfo
    from apeiria.core.services.cache import get_cache
    from apeiria.core.utils.helpers import get_plugin_protection_reason

    async with get_session() as session:
        result = await session.execute(
            select(PluginInfo).where(PluginInfo.module_name == module_name)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail=t("web_ui.plugins.not_found"))
        if not enabled:
            reason = get_plugin_protection_reason(module_name)
            if reason:
                raise HTTPException(
                    status_code=400,
                    detail=t("web_ui.plugins.protected", reason=reason),
                )
        record.is_global_enabled = enabled
        await session.commit()

    await get_cache().delete(f"plugin_global:{module_name}")
    return {"status": "ok"}
