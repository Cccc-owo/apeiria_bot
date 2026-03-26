"""Plugin routes — list and manage plugins."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from apeiria.core.i18n import t
from apeiria.domains.exceptions import ProtectedPluginError, ResourceNotFoundError
from apeiria.domains.plugins import (
    AdapterConfigState,
    DriverConfigState,
    PluginConfigConflictError,
    PluginConfigState,
    PluginRawSettingsState,
    PluginSettingsNotConfigurableError,
    PluginSettingsState,
    plugin_catalog_service,
    plugin_config_view_service,
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

router = APIRouter()


def _to_adapter_config_response(state: AdapterConfigState) -> AdapterConfigResponse:
    modules = state.modules
    return AdapterConfigResponse(
        modules=[
            AdapterConfigItem(
                name=item.name,
                is_loaded=item.is_loaded,
                is_importable=item.is_importable,
            )
            for item in modules
        ]
    )


def _to_driver_config_response(state: DriverConfigState) -> DriverConfigResponse:
    builtin = state.builtin
    return DriverConfigResponse(
        builtin=[
            DriverConfigItem(
                name=item.name,
                is_active=item.is_active,
            )
            for item in builtin
        ]
    )


def _to_plugin_config_response(state: PluginConfigState) -> PluginConfigResponse:
    modules = state.modules
    dirs = state.dirs
    return PluginConfigResponse(
        modules=[
            PluginConfigModuleItem(
                name=item.name,
                is_loaded=item.is_loaded,
                is_importable=item.is_importable,
            )
            for item in modules
        ],
        dirs=[
            PluginConfigDirItem(
                path=item.path,
                exists=item.exists,
                is_loaded=item.is_loaded,
            )
            for item in dirs
        ],
    )


def _to_plugin_settings_response(state: PluginSettingsState) -> PluginSettingsResponse:
    fields = state.fields
    return PluginSettingsResponse(
        module_name=state.module_name,
        section=state.section,
        legacy_flatten=state.legacy_flatten,
        config_source=state.config_source,
        has_config_model=state.has_config_model,
        fields=[
            PluginSettingFieldItem(
                key=item.key,
                type=item.type,
                editor=item.editor,
                item_type=item.item_type,
                key_type=item.key_type,
                default=item.default,
                help=item.help,
                choices=item.choices,
                current_value=item.current_value,
                local_value=item.local_value,
                value_source=item.value_source,
                global_key=item.global_key,
                has_local_override=item.has_local_override,
                allows_null=item.allows_null,
                editable=item.editable,
                type_category=item.type_category,
            )
            for item in fields
        ],
    )


def _to_plugin_raw_settings_response(
    state: PluginRawSettingsState,
) -> PluginRawSettingsResponse:
    return PluginRawSettingsResponse(
        module_name=state.module_name,
        section=state.section,
        text=state.text,
    )


def _raise_settings_error(exc: Exception) -> None:
    if isinstance(exc, PluginConfigConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, PluginSettingsNotConfigurableError):
        raise HTTPException(
            status_code=404,
            detail="plugin has no configurable fields",
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.get("/adapters/config", response_model=AdapterConfigResponse)
async def get_adapter_config(
    _: Annotated[Any, Depends(require_auth)],
) -> AdapterConfigResponse:
    return _to_adapter_config_response(plugin_config_view_service.get_adapter_config())


@router.patch("/adapters/config", response_model=AdapterConfigResponse)
async def update_adapter_config(
    payload: AdapterConfigRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> AdapterConfigResponse:
    return _to_adapter_config_response(
        plugin_config_view_service.update_adapter_config(payload.modules)
    )


@router.get("/drivers/config", response_model=DriverConfigResponse)
async def get_driver_config(
    _: Annotated[Any, Depends(require_auth)],
) -> DriverConfigResponse:
    return _to_driver_config_response(plugin_config_view_service.get_driver_config())


@router.patch("/drivers/config", response_model=DriverConfigResponse)
async def update_driver_config(
    payload: DriverConfigRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> DriverConfigResponse:
    return _to_driver_config_response(
        plugin_config_view_service.update_driver_config(payload.builtin)
    )


@router.get("/config", response_model=PluginConfigResponse)
async def get_plugin_config(
    _: Annotated[Any, Depends(require_auth)],
) -> PluginConfigResponse:
    return _to_plugin_config_response(plugin_config_view_service.get_plugin_config())


@router.patch("/config", response_model=PluginConfigResponse)
async def update_plugin_config(
    payload: PluginConfigRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginConfigResponse:
    return _to_plugin_config_response(
        plugin_config_view_service.update_plugin_config(
            payload.modules,
            payload.dirs,
        )
    )


@router.get("/core/settings", response_model=PluginSettingsResponse)
async def get_core_settings(
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    return _to_plugin_settings_response(plugin_config_view_service.get_core_settings())


@router.get("/core/settings/raw", response_model=PluginRawSettingsResponse)
async def get_core_settings_raw(
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    return _to_plugin_raw_settings_response(
        plugin_config_view_service.get_core_settings_raw()
    )


@router.patch("/core/settings", response_model=PluginSettingsResponse)
async def update_core_settings(
    payload: PluginSettingsUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    try:
        state = plugin_config_view_service.update_core_settings(
            payload.values,
            payload.clear,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_settings_error(exc)
    return _to_plugin_settings_response(state)


@router.patch("/core/settings/raw", response_model=PluginRawSettingsResponse)
async def update_core_settings_raw(
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    try:
        state = plugin_config_view_service.update_core_settings_raw(payload.text)
    except Exception as exc:  # noqa: BLE001
        _raise_settings_error(exc)
    return _to_plugin_raw_settings_response(state)


@router.get("/{module_name}/settings", response_model=PluginSettingsResponse)
async def get_plugin_settings(
    module_name: str,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    try:
        state = plugin_config_view_service.get_plugin_settings(module_name)
    except Exception as exc:  # noqa: BLE001
        _raise_settings_error(exc)
    return _to_plugin_settings_response(state)


@router.get("/{module_name}/settings/raw", response_model=PluginRawSettingsResponse)
async def get_plugin_settings_raw(
    module_name: str,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    try:
        state = plugin_config_view_service.get_plugin_settings_raw(module_name)
    except Exception as exc:  # noqa: BLE001
        _raise_settings_error(exc)
    return _to_plugin_raw_settings_response(state)


@router.patch("/{module_name}/settings", response_model=PluginSettingsResponse)
async def update_plugin_settings(
    module_name: str,
    payload: PluginSettingsUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginSettingsResponse:
    try:
        state = plugin_config_view_service.update_plugin_settings(
            module_name,
            payload.values,
            payload.clear,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_settings_error(exc)
    return _to_plugin_settings_response(state)


@router.patch("/{module_name}/settings/raw", response_model=PluginRawSettingsResponse)
async def update_plugin_settings_raw(
    module_name: str,
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginRawSettingsResponse:
    try:
        state = plugin_config_view_service.update_plugin_settings_raw(
            module_name,
            payload.text,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_settings_error(exc)
    return _to_plugin_raw_settings_response(state)


@router.get("/", response_model=list[PluginItem])
async def list_plugins(_: Annotated[Any, Depends(require_auth)]) -> list[PluginItem]:
    plugins = await plugin_catalog_service.list_plugins()
    return [
        PluginItem(
            module_name=plugin.module_name,
            name=plugin.name,
            description=plugin.description,
            source=plugin.source,
            is_global_enabled=plugin.is_global_enabled,
            is_protected=plugin.is_protected,
            protected_reason=plugin.protected_reason,
            plugin_type=plugin.plugin_type,
            admin_level=plugin.admin_level,
            author=plugin.author,
            version=plugin.version,
            required_plugins=plugin.required_plugins,
            dependent_plugins=plugin.dependent_plugins,
        )
        for plugin in plugins
    ]


@router.patch("/{module_name}")
async def update_plugin(
    module_name: str,
    _: Annotated[Any, Depends(require_auth)],
    *,
    enabled: bool = True,
) -> dict[str, str]:
    try:
        await plugin_catalog_service.set_plugin_enabled(module_name, enabled=enabled)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.plugins.not_found"),
        ) from None
    except ProtectedPluginError as exc:
        raise HTTPException(
            status_code=400,
            detail=t("web_ui.plugins.protected", reason=str(exc)),
        ) from None
    return {"status": "ok"}
