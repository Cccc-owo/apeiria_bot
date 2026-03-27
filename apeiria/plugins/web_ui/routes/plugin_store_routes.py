"""Plugin store routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apeiria.cli_store import uninstall_plugin_package
from apeiria.domains.plugin_store import (
    PluginStoreInstallRequest as PluginStoreInstallCommand,
)
from apeiria.domains.plugin_store import (
    StoreItemsQuery,
    plugin_store_service,
    plugin_store_task_service,
)
from apeiria.plugins.web_ui.auth import require_control_panel, require_owner
from apeiria.plugins.web_ui.models import (
    PluginStoreInstallRequest,
    PluginStoreItem,
    PluginStoreItemsResponse,
    PluginStoreRevertInstallRequest,
    PluginStoreSourceItem,
    PluginStoreTaskItem,
)

router = APIRouter()


class PluginStoreItemsQueryParams(BaseModel):
    """Plugin store list query params."""

    source: str = ""
    search: str = ""
    category: str = ""
    sort: str = "default"
    installed_only: bool = False
    uninstalled_only: bool = False
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=16, ge=1, le=100)


@router.get("/sources", response_model=list[PluginStoreSourceItem])
async def list_plugin_store_sources(
    _: Annotated[Any, Depends(require_control_panel)],
) -> list[PluginStoreSourceItem]:
    return [
        PluginStoreSourceItem(
            source_id=item.source_id,
            name=item.name,
            kind=item.kind,
            enabled=item.enabled,
            is_builtin=item.is_builtin,
            is_official=item.is_official,
            base_url=item.base_url,
            last_synced_at=item.last_synced_at,
            last_error=item.last_error,
        )
        for item in plugin_store_service.list_sources()
    ]


@router.get("/items", response_model=PluginStoreItemsResponse)
async def list_plugin_store_items(
    _: Annotated[Any, Depends(require_control_panel)],
    params: Annotated[PluginStoreItemsQueryParams, Depends()],
) -> PluginStoreItemsResponse:
    result = await plugin_store_service.list_items(
        StoreItemsQuery(
            source_id=params.source,
            search=params.search,
            category=params.category,
            sort=params.sort,
            installed_only=params.installed_only,
            uninstalled_only=params.uninstalled_only,
            page=params.page,
            per_page=params.per_page,
        )
    )
    return PluginStoreItemsResponse(
        items=[
            PluginStoreItem(
                source_id=item.source_id,
                source_name=item.source_name,
                plugin_id=item.plugin_id,
                name=item.name,
                module_name=item.module_name,
                package_name=item.package_name,
                description=item.description,
                project_link=item.project_link,
                homepage=item.homepage,
                author=item.author,
                author_link=item.author_link,
                version=item.version,
                tags=item.tags,
                is_official=item.is_official,
                publish_time=item.publish_time,
                extra=item.extra,
                is_installed=item.is_installed,
                is_registered=item.is_registered,
                installed_package=item.installed_package,
                installed_module_names=item.installed_module_names,
            )
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


@router.post("/install", response_model=PluginStoreTaskItem)
async def install_plugin_store_item(
    payload: PluginStoreInstallRequest,
    _: Annotated[Any, Depends(require_owner)],
) -> PluginStoreTaskItem:
    try:
        task = await plugin_store_task_service.create_plugin_install_task(
            PluginStoreInstallCommand(
                source_id=payload.source_id,
                plugin_id=payload.plugin_id,
                package_name=payload.package_name,
                module_name=payload.module_name,
            )
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


@router.get("/tasks/{task_id}", response_model=PluginStoreTaskItem)
async def get_plugin_store_task(
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


@router.post("/revert-install")
async def revert_plugin_store_install(
    payload: PluginStoreRevertInstallRequest,
    _: Annotated[Any, Depends(require_owner)],
) -> dict[str, str]:
    try:
        uninstall_plugin_package(
            payload.package_name,
            payload.module_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}
