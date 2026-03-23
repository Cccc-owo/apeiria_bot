"""Plugin routes — list and manage plugins."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import Annotated, Any

import nonebot
from fastapi import APIRouter, Depends, HTTPException

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
)
from apeiria.user_adapters import (
    read_project_adapter_config,
    write_project_adapter_config,
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

router = APIRouter()


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
    config = {
        "modules": sorted({item.strip() for item in payload.modules if item.strip()}),
        "packages": {
            package_name: [item for item in modules if item in payload.modules]
            for package_name, modules in current["packages"].items()
        },
    }
    config["packages"] = {
        package_name: modules
        for package_name, modules in config["packages"].items()
        if modules
    }
    write_project_adapter_config(config)
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
    config = {
        "builtin": sorted({item.strip() for item in payload.builtin if item.strip()}),
        "packages": {
            package_name: [item for item in builtin if item in payload.builtin]
            for package_name, builtin in current["packages"].items()
        },
    }
    config["packages"] = {
        package_name: builtin
        for package_name, builtin in config["packages"].items()
        if builtin
    }
    write_project_driver_config(config)
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


@router.patch("/config", response_model=PluginConfigResponse)
async def update_plugin_config(
    payload: PluginConfigRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> PluginConfigResponse:
    current = read_project_plugin_config()
    config = {
        "modules": sorted({item.strip() for item in payload.modules if item.strip()}),
        "dirs": sorted({item.strip() for item in payload.dirs if item.strip()}),
        "packages": {
            package_name: [item for item in modules if item in payload.modules]
            for package_name, modules in current["packages"].items()
        },
    }
    config["packages"] = {
        package_name: modules
        for package_name, modules in config["packages"].items()
        if modules
    }
    write_project_plugin_config(config)
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
        enabled_map = dict(result.all())

    result: list[PluginItem] = []
    for plugin in nonebot.get_loaded_plugins():
        meta = plugin.metadata
        protected_reason = get_plugin_protection_reason(plugin.module_name)
        result.append(
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
    return result


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
