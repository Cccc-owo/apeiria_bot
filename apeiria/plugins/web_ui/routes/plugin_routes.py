"""Plugin routes — list and manage plugins."""

from __future__ import annotations

import mimetypes
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from apeiria.core.i18n import t
from apeiria.core.services.plugin_update_check import (
    plugin_update_check_service,
    supports_plugin_update_check,
)
from apeiria.domains.exceptions import ProtectedPluginError, ResourceNotFoundError
from apeiria.domains.plugin_store import plugin_store_task_service
from apeiria.domains.plugins import (
    AdapterConfigState,
    DriverConfigState,
    PluginConfigConflictError,
    PluginConfigState,
    PluginRawSettingsState,
    PluginRawValidationState,
    PluginReadme,
    PluginSettingsNotConfigurableError,
    PluginSettingsState,
    plugin_catalog_service,
    plugin_config_view_service,
)
from apeiria.domains.plugins import (
    OrphanPluginConfigItem as DomainOrphanPluginConfigItem,
)
from apeiria.plugins.web_ui.auth import require_control_panel, require_owner
from apeiria.plugins.web_ui.models import (
    AdapterConfigItem,
    AdapterConfigRequest,
    AdapterConfigResponse,
    DriverConfigItem,
    DriverConfigRequest,
    DriverConfigResponse,
    OperationStatusResponse,
    OrphanPluginConfigItem,
    OrphanPluginConfigResponse,
    PluginConfigDirItem,
    PluginConfigModuleItem,
    PluginConfigRequest,
    PluginConfigResponse,
    PluginItem,
    PluginManualInstallRequest,
    PluginPackageUpdateRequest,
    PluginRawSettingsResponse,
    PluginReadmeResponse,
    PluginSettingFieldItem,
    PluginSettingsRawUpdateRequest,
    PluginSettingsRawValidationResponse,
    PluginSettingsResponse,
    PluginSettingsUpdateRequest,
    PluginStoreTaskItem,
    PluginTogglePreviewResponse,
    PluginToggleResponse,
    PluginUninstallRequest,
    PluginUpdateCheckItem,
    PluginUpdateCheckRequest,
)

router = APIRouter()


class _PluginTogglePreviewQuery(BaseModel):
    enabled: bool


def _to_orphan_plugin_config_response(
    items: list[DomainOrphanPluginConfigItem],
) -> OrphanPluginConfigResponse:
    return OrphanPluginConfigResponse(
        items=[
            OrphanPluginConfigItem(
                section=item.section,
                module_name=item.module_name,
                has_section=item.has_section,
                reason=item.reason,
            )
            for item in items
        ]
    )


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
                schema_=item.schema,
                default=item.default,
                help=item.help,
                choices=item.choices,
                base_value=item.base_value,
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


def _to_plugin_readme_response(state: PluginReadme) -> PluginReadmeResponse:
    return PluginReadmeResponse(
        module_name=state.module_name,
        filename=state.filename,
        content=state.content,
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


def _to_raw_validation_response(
    state: PluginRawValidationState,
) -> PluginSettingsRawValidationResponse:
    return PluginSettingsRawValidationResponse(
        valid=state.valid,
        message=state.message,
        line=state.line,
        column=state.column,
    )


@router.get("/adapters/config", response_model=AdapterConfigResponse)
async def get_adapter_config(
    _: Annotated[Any, Depends(require_control_panel)],
) -> AdapterConfigResponse:
    return _to_adapter_config_response(plugin_config_view_service.get_adapter_config())


@router.patch("/adapters/config", response_model=AdapterConfigResponse)
async def update_adapter_config(
    payload: AdapterConfigRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> AdapterConfigResponse:
    return _to_adapter_config_response(
        plugin_config_view_service.update_adapter_config(payload.modules)
    )


@router.get("/drivers/config", response_model=DriverConfigResponse)
async def get_driver_config(
    _: Annotated[Any, Depends(require_control_panel)],
) -> DriverConfigResponse:
    return _to_driver_config_response(plugin_config_view_service.get_driver_config())


@router.patch("/drivers/config", response_model=DriverConfigResponse)
async def update_driver_config(
    payload: DriverConfigRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> DriverConfigResponse:
    return _to_driver_config_response(
        plugin_config_view_service.update_driver_config(payload.builtin)
    )


@router.get("/config", response_model=PluginConfigResponse)
async def get_plugin_config(
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginConfigResponse:
    return _to_plugin_config_response(plugin_config_view_service.get_plugin_config())


@router.patch("/config", response_model=PluginConfigResponse)
async def update_plugin_config(
    payload: PluginConfigRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginConfigResponse:
    return _to_plugin_config_response(
        plugin_config_view_service.update_plugin_config(
            payload.modules,
            payload.dirs,
        )
    )


@router.get("/core/settings", response_model=PluginSettingsResponse)
async def get_core_settings(
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginSettingsResponse:
    return _to_plugin_settings_response(plugin_config_view_service.get_core_settings())


@router.get("/core/settings/raw", response_model=PluginRawSettingsResponse)
async def get_core_settings_raw(
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginRawSettingsResponse:
    return _to_plugin_raw_settings_response(
        plugin_config_view_service.get_core_settings_raw()
    )


@router.patch("/core/settings", response_model=PluginSettingsResponse)
async def update_core_settings(
    payload: PluginSettingsUpdateRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginSettingsResponse:
    try:
        state = plugin_config_view_service.update_core_settings(
            payload.values,
            payload.clear,
        )
    except Exception as exc:
        _raise_settings_error(exc)
        raise AssertionError("unreachable") from exc
    return _to_plugin_settings_response(state)


@router.patch("/core/settings/raw", response_model=PluginRawSettingsResponse)
async def update_core_settings_raw(
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginRawSettingsResponse:
    try:
        state = plugin_config_view_service.update_core_settings_raw(payload.text)
    except Exception as exc:
        _raise_settings_error(exc)
        raise AssertionError("unreachable") from exc
    return _to_plugin_raw_settings_response(state)


@router.post(
    "/core/settings/raw/validate",
    response_model=PluginSettingsRawValidationResponse,
)
async def validate_core_settings_raw(
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginSettingsRawValidationResponse:
    return _to_raw_validation_response(
        plugin_config_view_service.validate_core_settings_raw(payload.text)
    )


@router.get("/{module_name}/settings", response_model=PluginSettingsResponse)
async def get_plugin_settings(
    module_name: str,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginSettingsResponse:
    try:
        state = plugin_config_view_service.get_plugin_settings(module_name)
    except Exception as exc:
        _raise_settings_error(exc)
        raise AssertionError("unreachable") from exc
    return _to_plugin_settings_response(state)


@router.get("/{module_name}/settings/raw", response_model=PluginRawSettingsResponse)
async def get_plugin_settings_raw(
    module_name: str,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginRawSettingsResponse:
    try:
        state = plugin_config_view_service.get_plugin_settings_raw(module_name)
    except Exception as exc:
        _raise_settings_error(exc)
        raise AssertionError("unreachable") from exc
    return _to_plugin_raw_settings_response(state)


@router.get("/{module_name}/readme", response_model=PluginReadmeResponse)
async def get_plugin_readme(
    module_name: str,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginReadmeResponse:
    try:
        state = await plugin_catalog_service.get_plugin_readme(module_name)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.plugins.readme_not_found"),
        ) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_plugin_readme_response(state)


@router.get("/{module_name}/readme/asset")
async def get_plugin_readme_asset(
    module_name: str,
    path: Annotated[str, Query(min_length=1)],
    _: Annotated[Any, Depends(require_control_panel)],
) -> FileResponse:
    try:
        asset_path = await plugin_catalog_service.get_plugin_readme_asset_path(
            module_name,
            path,
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.plugins.readme_not_found"),
        ) from None
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=t("web_ui.plugins.readme_asset_forbidden"),
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_type, _ = mimetypes.guess_type(asset_path.name)
    return FileResponse(
        asset_path,
        media_type=media_type or "application/octet-stream",
        filename=asset_path.name,
        headers={
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch("/{module_name}/settings", response_model=PluginSettingsResponse)
async def update_plugin_settings(
    module_name: str,
    payload: PluginSettingsUpdateRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginSettingsResponse:
    try:
        state = plugin_config_view_service.update_plugin_settings(
            module_name,
            payload.values,
            payload.clear,
        )
    except Exception as exc:
        _raise_settings_error(exc)
        raise AssertionError("unreachable") from exc
    return _to_plugin_settings_response(state)


@router.patch("/{module_name}/settings/raw", response_model=PluginRawSettingsResponse)
async def update_plugin_settings_raw(
    module_name: str,
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginRawSettingsResponse:
    try:
        state = plugin_config_view_service.update_plugin_settings_raw(
            module_name,
            payload.text,
        )
    except Exception as exc:
        _raise_settings_error(exc)
        raise AssertionError("unreachable") from exc
    return _to_plugin_raw_settings_response(state)


@router.post(
    "/{module_name}/settings/raw/validate",
    response_model=PluginSettingsRawValidationResponse,
)
async def validate_plugin_settings_raw(
    module_name: str,
    payload: PluginSettingsRawUpdateRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginSettingsRawValidationResponse:
    try:
        state = plugin_config_view_service.validate_plugin_settings_raw(
            module_name,
            payload.text,
        )
    except Exception as exc:
        _raise_settings_error(exc)
        raise AssertionError("unreachable") from exc
    return _to_raw_validation_response(state)


@router.get("/", response_model=list[PluginItem])
async def list_plugins(
    _: Annotated[Any, Depends(require_control_panel)],
) -> list[PluginItem]:
    plugins = await plugin_catalog_service.list_plugins()
    return [
        PluginItem(
            module_name=plugin.module_name,
            kind=plugin.kind,
            access_mode=plugin.access_mode,
            name=plugin.name,
            description=plugin.description,
            homepage=plugin.homepage,
            source=plugin.source,
            is_global_enabled=plugin.is_global_enabled,
            is_protected=plugin.is_protected,
            protected_reason=plugin.protected_reason,
            plugin_type=plugin.plugin_type,
            admin_level=plugin.admin_level,
            author=plugin.author,
            version=plugin.version,
            is_loaded=plugin.is_loaded,
            is_explicit=plugin.is_explicit,
            is_dependency=plugin.is_dependency,
            is_pending_uninstall=plugin.is_pending_uninstall,
            can_edit_config=plugin.can_edit_config,
            can_view_readme=plugin.can_view_readme,
            can_enable_disable=plugin.can_enable_disable,
            can_uninstall=plugin.can_uninstall,
            can_package_update=(
                plugin.can_uninstall
                and bool(plugin.installed_package)
                and supports_plugin_update_check(plugin.installed_package)
            ),
            child_plugins=plugin.child_plugins,
            required_plugins=plugin.required_plugins,
            dependent_plugins=plugin.dependent_plugins,
            installed_package=plugin.installed_package,
            installed_module_names=plugin.installed_module_names,
        )
        for plugin in plugins
    ]


@router.post("/update-checks", response_model=list[PluginUpdateCheckItem])
async def check_plugin_updates(
    payload: PluginUpdateCheckRequest,
    _: Annotated[Any, Depends(require_control_panel)],
) -> list[PluginUpdateCheckItem]:
    plugins = await plugin_catalog_service.list_plugins()
    results = await plugin_update_check_service.check_plugins(
        plugins,
        force_refresh=payload.force_refresh,
    )
    return [
        PluginUpdateCheckItem(
            module_name=item.module_name,
            package_name=item.package_name,
            current_version=item.current_version,
            latest_version=item.latest_version,
            has_update=item.has_update,
            checked=item.checked,
            error=item.error,
        )
        for item in results
    ]


@router.patch("/{module_name}", response_model=PluginToggleResponse)
async def update_plugin(
    module_name: str,
    _: Annotated[Any, Depends(require_control_panel)],
    *,
    enabled: bool = True,
    cascade: bool = False,
) -> PluginToggleResponse:
    try:
        result = await plugin_catalog_service.apply_plugin_toggle(
            module_name,
            enabled=enabled,
            cascade=cascade,
        )
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PluginToggleResponse(
        module_name=result.module_name,
        enabled=result.enabled,
        affected_modules=result.affected_modules,
    )


@router.get("/{module_name}/toggle-preview", response_model=PluginTogglePreviewResponse)
async def preview_toggle_plugin(
    module_name: str,
    query: Annotated[_PluginTogglePreviewQuery, Depends()],
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginTogglePreviewResponse:
    try:
        preview = await plugin_catalog_service.preview_toggle_plugin(
            module_name,
            enabled=query.enabled,
        )
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.plugins.not_found"),
        ) from None
    return PluginTogglePreviewResponse(
        module_name=preview.module_name,
        enabled=preview.enabled,
        allowed=preview.allowed,
        summary=preview.summary,
        blocked_reason=preview.blocked_reason,
        requires_enable=preview.requires_enable,
        requires_disable=preview.requires_disable,
        protected_dependents=preview.protected_dependents,
        missing_dependencies=preview.missing_dependencies,
    )


@router.post("/{module_name}/uninstall", response_model=OperationStatusResponse)
async def uninstall_plugin(
    module_name: str,
    payload: PluginUninstallRequest,
    _: Annotated[Any, Depends(require_owner)],
) -> OperationStatusResponse:
    try:
        await plugin_catalog_service.uninstall_plugin(
            module_name,
            remove_config=payload.remove_config,
        )
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OperationStatusResponse(status="ok")


@router.get("/orphan-configs", response_model=OrphanPluginConfigResponse)
async def list_orphan_plugin_configs(
    _: Annotated[Any, Depends(require_owner)],
) -> OrphanPluginConfigResponse:
    items = await plugin_catalog_service.list_orphan_plugin_configs()
    return _to_orphan_plugin_config_response(items)


@router.post("/orphan-configs/cleanup", response_model=OrphanPluginConfigResponse)
async def cleanup_orphan_plugin_configs(
    _: Annotated[Any, Depends(require_owner)],
) -> OrphanPluginConfigResponse:
    items = await plugin_catalog_service.cleanup_orphan_plugin_configs()
    return _to_orphan_plugin_config_response(items)


@router.post("/install/manual", response_model=PluginStoreTaskItem)
async def install_plugin_manual(
    payload: PluginManualInstallRequest,
    _: Annotated[Any, Depends(require_owner)],
) -> PluginStoreTaskItem:
    try:
        task = await plugin_store_task_service.create_manual_plugin_install_task(
            payload.requirement,
            payload.module_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PluginStoreTaskItem(
        task_id=task.task_id,
        title=task.title,
        status=task.status,
        logs=task.logs,
        error=task.error,
        result=task.result,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


@router.post("/{module_name}/update", response_model=PluginStoreTaskItem)
async def update_plugin_package_task(
    module_name: str,
    payload: PluginPackageUpdateRequest,
    _: Annotated[Any, Depends(require_owner)],
) -> PluginStoreTaskItem:
    plugin = await plugin_catalog_service.get_plugin(module_name)
    if plugin is None:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.plugins.not_found"),
        ) from None
    if (
        not plugin.can_uninstall
        or plugin.installed_package != payload.package_name
        or not supports_plugin_update_check(payload.package_name)
    ):
        raise HTTPException(
            status_code=400,
            detail="plugin package update is not allowed",
        ) from None

    try:
        task = await plugin_store_task_service.create_manual_plugin_update_task(
            payload.package_name,
            module_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PluginStoreTaskItem(
        task_id=task.task_id,
        title=task.title,
        status=task.status,
        logs=task.logs,
        error=task.error,
        result=task.result,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


@router.get("/install/tasks/{task_id}", response_model=PluginStoreTaskItem)
async def get_plugin_install_task(
    task_id: str,
    _: Annotated[Any, Depends(require_control_panel)],
) -> PluginStoreTaskItem:
    task = plugin_store_task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return PluginStoreTaskItem(
        task_id=task.task_id,
        title=task.title,
        status=task.status,
        logs=task.logs,
        error=task.error,
        result=task.result,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )
