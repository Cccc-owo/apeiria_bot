"""Plugin domain services."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import distributions, packages_distributions
from pathlib import Path

import nonebot

from apeiria.cli_store import PluginUninstallResult
from apeiria.config.plugins import plugin_config_service
from apeiria.core.utils.helpers import (
    find_loaded_plugin,
    get_plugin_dependents,
    get_plugin_extra,
    get_plugin_name,
    get_plugin_protection_reason,
    get_plugin_required_plugins,
    get_plugin_source,
)
from apeiria.domains.exceptions import ProtectedPluginError, ResourceNotFoundError
from apeiria.domains.permissions import permission_service
from apeiria.domains.plugins.repository import plugin_catalog_repository
from apeiria.package_ids import normalize_package_id
from apeiria.runtime_env import (
    declared_plugin_requirements,
    enqueue_plugin_requirement_removal,
    resolve_declared_plugin_requirement,
)


@dataclass(frozen=True)
class PluginCatalogItem:
    """Normalized plugin list entry."""

    module_name: str
    name: str
    description: str | None
    source: str
    is_global_enabled: bool
    is_protected: bool
    protected_reason: str | None
    plugin_type: str
    admin_level: int
    author: str | None
    version: str | None
    required_plugins: list[str]
    dependent_plugins: list[str]
    installed_package: str | None
    installed_module_names: list[str]


class PluginCatalogService:
    """List and mutate plugin registry state."""

    async def list_plugins(self) -> list[PluginCatalogItem]:
        enabled_map = await plugin_catalog_repository.get_enabled_map()
        package_bindings = plugin_config_service.read_project_plugin_config()[
            "packages"
        ]
        top_level_packages = packages_distributions()

        items: list[PluginCatalogItem] = []
        for plugin in nonebot.get_loaded_plugins():
            meta = plugin.metadata
            extra = get_plugin_extra(plugin)
            protected_reason = get_plugin_protection_reason(plugin.module_name)
            installed_package = self._resolve_listed_installed_package(
                plugin.module_name,
                package_bindings,
                top_level_packages,
            )
            items.append(
                PluginCatalogItem(
                    module_name=plugin.module_name,
                    name=get_plugin_name(plugin),
                    description=meta.description if meta else None,
                    source=get_plugin_source(plugin),
                    is_global_enabled=enabled_map.get(plugin.module_name, True),
                    is_protected=protected_reason is not None,
                    protected_reason=protected_reason,
                    plugin_type=extra.plugin_type.value if extra else "normal",
                    admin_level=extra.admin_level if extra else 0,
                    author=extra.author if extra else None,
                    version=extra.version if extra else None,
                    required_plugins=get_plugin_required_plugins(plugin),
                    dependent_plugins=get_plugin_dependents(plugin.module_name),
                    installed_package=installed_package,
                    installed_module_names=sorted(
                        package_bindings.get(installed_package, [])
                    )
                    if installed_package in package_bindings
                    else [plugin.module_name]
                    if installed_package
                    else [],
                )
            )
        return items

    async def set_plugin_enabled(self, module_name: str, *, enabled: bool) -> None:
        if not enabled:
            reason = get_plugin_protection_reason(module_name)
            if reason:
                raise ProtectedPluginError(reason)

        await plugin_catalog_repository.set_plugin_enabled(
            module_name,
            enabled=enabled,
        )

        await permission_service.invalidate_plugin_global_cache(module_name)

    async def uninstall_plugin(self, module_name: str) -> PluginUninstallResult:
        plugin = find_loaded_plugin(module_name)
        if plugin is None:
            raise ResourceNotFoundError(module_name)

        reason = get_plugin_protection_reason(module_name)
        if reason:
            raise ProtectedPluginError(reason)
        if not self._is_plugin_uninstallable(plugin):
            msg = "only custom or external plugins can be uninstalled"
            raise ValueError(msg)

        current_config = plugin_config_service.read_project_plugin_config()
        package_name = self._resolve_installed_package(module_name, plugin)
        removal_requirement = self._resolve_removal_requirement(
            module_name,
            package_name,
            current_config["packages"],
        )
        plugin_config_service.remove_project_plugin_module(module_name)
        if removal_requirement:
            enqueue_plugin_requirement_removal(removal_requirement)
        result = PluginUninstallResult(
            requirement=removal_requirement or "",
            module_names=[module_name],
        )
        await permission_service.invalidate_plugin_global_cache(module_name)
        return result

    def _resolve_listed_installed_package(
        self,
        module_name: str,
        package_bindings: dict[str, list[str]],
        top_level_packages: dict[str, list[str]],
    ) -> str | None:
        for package_name, module_names in package_bindings.items():
            if module_name in module_names:
                return package_name
        top_level = module_name.split(".", 1)[0]
        inferred = top_level_packages.get(top_level, [])
        return inferred[0] if inferred else None

    def _resolve_installed_package(
        self,
        module_name: str,
        plugin: object | None = None,
    ) -> str | None:
        packages = plugin_config_service.read_project_plugin_config()["packages"]
        listed = self._resolve_listed_installed_package(
            module_name,
            packages,
            packages_distributions(),
        )
        if listed:
            return listed
        return self._infer_installed_package_from_module_file(plugin)

    def _infer_installed_package_from_module_file(
        self,
        plugin: object | None = None,
    ) -> str | None:
        module = getattr(plugin, "module", None)
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str) or not module_file:
            return None

        try:
            module_path = Path(module_file).resolve()
        except OSError:
            return None

        for dist in distributions():
            dist_name = dist.metadata.get("Name") or dist.name
            if not dist_name:
                continue
            for file in dist.files or ():
                try:
                    candidate = Path(dist.locate_file(file)).resolve()
                except OSError:
                    continue
                if candidate == module_path:
                    return str(dist_name)
        return None

    def _resolve_removal_requirement(
        self,
        module_name: str,
        package_name: str | None,
        package_bindings: dict[str, list[str]],
    ) -> str | None:
        if not package_name:
            return None

        declared = resolve_declared_plugin_requirement(package_name).strip()
        if not declared:
            return None

        normalized_declared = normalize_package_id(declared)
        if normalized_declared not in declared_plugin_requirements():
            return None

        bound_modules = package_bindings.get(package_name, [])
        if not bound_modules:
            return declared
        if len(bound_modules) == 1 and module_name in bound_modules:
            return declared
        return None

    def _is_plugin_uninstallable(self, plugin: object) -> bool:
        return get_plugin_source(plugin) in {"custom", "external"}


plugin_catalog_service = PluginCatalogService()
