"""Plugin domain services."""

from __future__ import annotations

from dataclasses import dataclass, replace
from importlib.metadata import distributions, packages_distributions
from pathlib import Path
from typing import TYPE_CHECKING

import nonebot

from apeiria.cli_store import PluginUninstallResult
from apeiria.config.plugins import plugin_config_service
from apeiria.config.project import project_config_service
from apeiria.core.i18n import t
from apeiria.core.plugin_policy import is_framework_dependency_plugin_module
from apeiria.core.utils.helpers import (
    find_loaded_plugin,
    get_module_required_plugins,
    get_pending_uninstall_plugin_modules,
    get_plugin_extra,
    get_plugin_name,
    get_plugin_protection_reason,
    get_plugin_required_plugins,
    get_plugin_source,
    get_plugin_source_by_module_name,
    invalidate_plugin_management_caches,
    is_module_importable,
)
from apeiria.domains.exceptions import ProtectedPluginError, ResourceNotFoundError
from apeiria.domains.permissions import permission_service
from apeiria.domains.plugins.repository import plugin_catalog_repository
from apeiria.domains.plugins.settings_support import get_plugin_declared_configs
from apeiria.package_ids import normalize_package_id
from apeiria.runtime_env import (
    declared_plugin_requirements,
    enqueue_plugin_module_uninstall,
    enqueue_plugin_requirement_removal,
    resolve_declared_plugin_requirement,
)

if TYPE_CHECKING:
    from nonebot.plugin import Plugin


@dataclass(frozen=True)
class _PluginListContext:
    enabled_map: dict[str, bool]
    package_bindings: dict[str, list[str]]
    pending_uninstall_modules: set[str]
    top_level_packages: dict[str, list[str]]


@dataclass(frozen=True)
class _PluginItemFacts:
    is_explicit: bool
    is_dependency: bool
    required_plugins: list[str]
    dependent_plugins: list[str]


@dataclass(frozen=True)
class PluginCatalogItem:
    """Normalized plugin list entry."""

    module_name: str
    name: str
    description: str | None
    homepage: str | None
    source: str
    is_global_enabled: bool
    is_protected: bool
    protected_reason: str | None
    plugin_type: str
    admin_level: int
    author: str | None
    version: str | None
    is_loaded: bool
    is_explicit: bool
    is_dependency: bool
    is_pending_uninstall: bool
    can_edit_config: bool
    can_enable_disable: bool
    can_uninstall: bool
    child_plugins: list[str]
    required_plugins: list[str]
    dependent_plugins: list[str]
    installed_package: str | None
    installed_module_names: list[str]


@dataclass(frozen=True)
class OrphanPluginConfigItem:
    """One orphaned plugin config entry in project config."""

    section: str
    module_name: str | None
    has_section: bool
    reason: str


class PluginCatalogService:
    """List and mutate plugin registry state."""

    async def list_plugins(self) -> list[PluginCatalogItem]:
        enabled_map = await plugin_catalog_repository.get_enabled_map()
        project_plugin_config = plugin_config_service.read_project_plugin_config()
        explicit_modules = set(project_plugin_config["modules"])
        package_bindings = project_plugin_config["packages"]
        pending_uninstall_modules = get_pending_uninstall_plugin_modules()
        loaded_plugins = {
            plugin.module_name: plugin
            for plugin in nonebot.get_loaded_plugins()
        }
        loaded_modules = set(loaded_plugins)

        required_by_module: dict[str, list[str]] = {}
        display_name_by_module: dict[str, str] = {}

        for module_name, plugin in loaded_plugins.items():
            required_by_module[module_name] = get_plugin_required_plugins(plugin)
            display_name_by_module[module_name] = get_plugin_name(plugin)

        pending_uninstall_modules = self._expand_pending_uninstall_modules(
            loaded_plugins=loaded_plugins,
            explicit_modules=explicit_modules,
            seed_modules=pending_uninstall_modules,
            required_by_module=required_by_module,
        )
        top_level_packages = packages_distributions()
        build_context = _PluginListContext(
            enabled_map=enabled_map,
            package_bindings=package_bindings,
            pending_uninstall_modules=pending_uninstall_modules,
            top_level_packages=top_level_packages,
        )

        for module_name in sorted(explicit_modules - loaded_modules):
            required_by_module[module_name] = get_module_required_plugins(module_name)
            display_name_by_module.setdefault(module_name, module_name)

        dependency_modules = {
            dependency
            for dependencies in required_by_module.values()
            for dependency in dependencies
        }
        importable_modules = {
            module_name
            for module_name in (dependency_modules | explicit_modules)
            if is_module_importable(module_name)
        }
        visible_dependency_modules = {
            module_name
            for module_name in dependency_modules
            if module_name in importable_modules
        }
        candidate_modules = (
            loaded_modules
            | explicit_modules
            | visible_dependency_modules
        )

        dependent_name_map: dict[str, set[str]] = {
            module_name: set() for module_name in candidate_modules
        }
        for owner_module, dependencies in required_by_module.items():
            if owner_module in pending_uninstall_modules:
                continue
            owner_name = display_name_by_module.get(owner_module, owner_module)
            for dependency in dependencies:
                if dependency not in dependent_name_map:
                    dependent_name_map[dependency] = set()
                dependent_name_map[dependency].add(owner_name)

        items: list[PluginCatalogItem] = []
        for module_name in sorted(candidate_modules):
            is_loaded = module_name in loaded_plugins
            is_explicit = module_name in explicit_modules
            is_dependency = module_name in dependency_modules
            required_plugins = required_by_module.get(module_name, [])
            dependent_plugins = sorted(dependent_name_map.get(module_name, set()))
            facts = _PluginItemFacts(
                is_explicit=is_explicit,
                is_dependency=is_dependency,
                required_plugins=required_plugins,
                dependent_plugins=dependent_plugins,
            )

            if is_loaded:
                items.append(
                    self._build_loaded_plugin_item(
                        plugin=loaded_plugins[module_name],
                        context=build_context,
                        facts=facts,
                    )
                )
                continue

            items.append(
                self._build_unloaded_plugin_item(
                    module_name=module_name,
                    context=build_context,
                    facts=facts,
                )
            )
        return self._collapse_child_plugins(items)

    async def set_plugin_enabled(self, module_name: str, *, enabled: bool) -> bool:
        plugin = find_loaded_plugin(module_name)
        if plugin is None:
            raise ResourceNotFoundError(module_name)

        if not enabled:
            reason = get_plugin_protection_reason(module_name)
            if reason:
                raise ProtectedPluginError(reason)

        try:
            changed = await plugin_catalog_repository.set_plugin_enabled(
                module_name,
                enabled=enabled,
            )
        except ResourceNotFoundError:
            await plugin_catalog_repository.ensure_plugin_record(plugin)
            changed = await plugin_catalog_repository.set_plugin_enabled(
                module_name,
                enabled=enabled,
            )

        await permission_service.invalidate_plugin_global_cache(module_name)
        return changed

    async def uninstall_plugin(
        self,
        module_name: str,
        *,
        remove_config: bool = False,
    ) -> PluginUninstallResult:
        plugin = find_loaded_plugin(module_name)
        if plugin is None:
            raise ResourceNotFoundError(module_name)

        reason = self._get_uninstall_block_reason(module_name)
        if reason:
            raise ProtectedPluginError(reason)
        if not self._is_plugin_uninstallable(plugin):
            msg = "only custom or external plugins can be uninstalled"
            raise ValueError(msg)

        current_config = plugin_config_service.read_project_plugin_config()
        loaded_plugins = {
            loaded.module_name: loaded
            for loaded in nonebot.get_loaded_plugins()
        }
        required_by_module = {
            loaded.module_name: get_plugin_required_plugins(loaded)
            for loaded in loaded_plugins.values()
        }
        explicit_modules = set(current_config["modules"])
        pending_modules = self._expand_pending_uninstall_modules(
            loaded_plugins=loaded_plugins,
            explicit_modules=explicit_modules,
            seed_modules=get_pending_uninstall_plugin_modules() | {module_name},
            required_by_module=required_by_module,
        )
        package_name = self._resolve_installed_package(module_name, plugin)
        removal_requirement = self._resolve_removal_requirement(
            module_name,
            package_name,
            current_config["packages"],
        )
        for pending_module in sorted(pending_modules):
            plugin_config_service.remove_project_plugin_module(pending_module)
            enqueue_plugin_module_uninstall(pending_module)
        if remove_config:
            for pending_module in sorted(pending_modules):
                if pending_module != module_name:
                    continue
                section = get_plugin_declared_configs(pending_module).section
                project_config_service.remove_project_plugin_section(section)
        if removal_requirement:
            enqueue_plugin_requirement_removal(removal_requirement)
        invalidate_plugin_management_caches()
        result = PluginUninstallResult(
            requirement=removal_requirement or "",
            module_names=sorted(pending_modules),
        )
        for pending_module in pending_modules:
            await permission_service.invalidate_plugin_global_cache(pending_module)
        return result

    async def list_orphan_plugin_configs(self) -> list[OrphanPluginConfigItem]:
        loaded_plugins = list(nonebot.get_loaded_plugins())
        loaded_sections = {
            get_plugin_declared_configs(plugin.module_name).section
            for plugin in loaded_plugins
        }
        loaded_modules = {
            plugin.module_name
            for plugin in loaded_plugins
        }
        section_names = project_config_service.read_project_plugin_section_names()
        module_map = project_config_service.read_project_plugin_module_map()

        orphaned: list[OrphanPluginConfigItem] = []
        seen_sections: set[str] = set()

        for section in section_names:
            mapped_module = module_map.get(section)
            if section in loaded_sections:
                continue
            if mapped_module and (
                mapped_module in loaded_modules
                or is_module_importable(mapped_module)
            ):
                continue
            orphaned.append(
                OrphanPluginConfigItem(
                    section=section,
                    module_name=mapped_module,
                    has_section=True,
                    reason=(
                        "mapped module is missing"
                        if mapped_module
                        else "no loaded plugin uses this section"
                    ),
                )
            )
            seen_sections.add(section)

        for section, module_name in module_map.items():
            if section in seen_sections or section in loaded_sections:
                continue
            if is_module_importable(module_name):
                continue
            orphaned.append(
                OrphanPluginConfigItem(
                    section=section,
                    module_name=module_name,
                    has_section=section in section_names,
                    reason="mapped module is missing",
                )
            )

        return sorted(orphaned, key=lambda item: item.section)

    async def cleanup_orphan_plugin_configs(self) -> list[OrphanPluginConfigItem]:
        orphaned = await self.list_orphan_plugin_configs()
        if not orphaned:
            return []

        mapping_updates: dict[str, None] = {}
        for item in orphaned:
            if item.has_section:
                project_config_service.remove_project_plugin_section(item.section)
            mapping_updates[item.section] = None

        if mapping_updates:
            project_config_service.write_project_plugin_module_map(mapping_updates)
        return orphaned

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

    def _build_loaded_plugin_item(
        self,
        *,
        plugin: Plugin,
        context: _PluginListContext,
        facts: _PluginItemFacts,
    ) -> PluginCatalogItem:
        meta = plugin.metadata
        extra = get_plugin_extra(plugin)
        plugin_source = get_plugin_source(plugin)
        installed_package = self._resolve_listed_installed_package(
            plugin.module_name,
            context.package_bindings,
            context.top_level_packages,
        )
        protected_reason = self._compose_protection_reason(
            plugin.module_name,
            facts.dependent_plugins,
        )
        can_enable_disable = (
            plugin.module_name not in context.pending_uninstall_modules
            and not is_framework_dependency_plugin_module(plugin.module_name)
        )
        uninstall_block_reason = self._get_uninstall_block_reason(plugin.module_name)
        can_uninstall = (
            facts.is_explicit
            and can_enable_disable
            and plugin_source in {"custom", "external"}
            and uninstall_block_reason is None
        )
        return PluginCatalogItem(
            module_name=plugin.module_name,
            name=get_plugin_name(plugin),
            description=meta.description if meta else None,
            homepage=meta.homepage if meta else None,
            source=plugin_source,
            is_global_enabled=context.enabled_map.get(plugin.module_name, True),
            is_protected=protected_reason is not None,
            protected_reason=protected_reason,
            plugin_type=extra.plugin_type.value if extra else "normal",
            admin_level=extra.admin_level if extra else 0,
            author=extra.author if extra else None,
            version=extra.version if extra else None,
            is_loaded=True,
            is_explicit=facts.is_explicit,
            is_dependency=facts.is_dependency,
            is_pending_uninstall=(
                plugin.module_name in context.pending_uninstall_modules
            ),
            can_edit_config=True,
            can_enable_disable=can_enable_disable,
            can_uninstall=can_uninstall,
            child_plugins=[],
            required_plugins=facts.required_plugins,
            dependent_plugins=facts.dependent_plugins,
            installed_package=installed_package,
            installed_module_names=sorted(
                context.package_bindings.get(installed_package, [])
            )
            if installed_package in context.package_bindings
            else [plugin.module_name]
            if installed_package
            else [],
        )

    def _build_unloaded_plugin_item(
        self,
        *,
        module_name: str,
        context: _PluginListContext,
        facts: _PluginItemFacts,
    ) -> PluginCatalogItem:
        installed_package = self._resolve_listed_installed_package(
            module_name,
            context.package_bindings,
            context.top_level_packages,
        )
        protected_reason = self._compose_protection_reason(
            module_name,
            facts.dependent_plugins,
        )
        is_importable = is_module_importable(module_name)
        return PluginCatalogItem(
            module_name=module_name,
            name=module_name,
            description=None,
            homepage=None,
            source=get_plugin_source_by_module_name(module_name),
            is_global_enabled=context.enabled_map.get(module_name, facts.is_explicit),
            is_protected=protected_reason is not None,
            protected_reason=protected_reason,
            plugin_type="normal",
            admin_level=0,
            author=None,
            version=None,
            is_loaded=False,
            is_explicit=facts.is_explicit,
            is_dependency=facts.is_dependency,
            is_pending_uninstall=module_name in context.pending_uninstall_modules,
            can_edit_config=is_importable or facts.is_explicit,
            can_enable_disable=False,
            can_uninstall=False,
            child_plugins=[],
            required_plugins=facts.required_plugins,
            dependent_plugins=facts.dependent_plugins,
            installed_package=installed_package,
            installed_module_names=sorted(
                context.package_bindings.get(installed_package, [])
            )
            if installed_package in context.package_bindings
            else [module_name]
            if installed_package
            else [],
        )

    def _compose_protection_reason(
        self,
        module_name: str,
        dependent_plugins: list[str],
    ) -> str | None:
        reasons = self._collect_core_block_reasons(module_name)
        if dependent_plugins:
            reasons.append(
                t(
                    "common.required_by_plugins",
                    plugins=", ".join(dependent_plugins),
                )
            )
        return "；".join(reasons) if reasons else None

    def _get_uninstall_block_reason(self, module_name: str) -> str | None:
        reasons = self._collect_core_block_reasons(module_name)
        return "；".join(reasons) if reasons else None

    def _collect_core_block_reasons(self, module_name: str) -> list[str]:
        reasons: list[str] = []
        if is_framework_dependency_plugin_module(module_name):
            reasons.append(t("common.framework_required"))
        if module_name == "apeiria.plugins.web_ui":
            reasons.append(t("common.control_panel_required"))
        return reasons

    def _expand_pending_uninstall_modules(
        self,
        *,
        loaded_plugins: dict[str, Plugin],
        explicit_modules: set[str],
        seed_modules: set[str],
        required_by_module: dict[str, list[str]],
    ) -> set[str]:
        pending = set(seed_modules) & set(loaded_plugins)
        if not pending:
            return pending

        while True:
            changed = False
            for module_name, plugin in loaded_plugins.items():
                if module_name in pending:
                    continue
                if module_name in explicit_modules:
                    continue
                plugin_source = get_plugin_source(plugin)
                if plugin_source not in {"custom", "external"}:
                    continue

                owners = {
                    owner_module
                    for owner_module, dependencies in required_by_module.items()
                    if module_name in dependencies
                }
                if owners and owners <= pending:
                    pending.add(module_name)
                    changed = True
            if not changed:
                return pending

    def _collapse_child_plugins(
        self,
        items: list[PluginCatalogItem],
    ) -> list[PluginCatalogItem]:
        item_map = {item.module_name: item for item in items}
        child_map: dict[str, list[str]] = {}
        hidden_children: set[str] = set()

        for item in items:
            parent_module = self._resolve_parent_plugin_module(item, item_map)
            if parent_module is None:
                continue
            child_map.setdefault(parent_module, []).append(item.module_name)
            hidden_children.add(item.module_name)

        collapsed: list[PluginCatalogItem] = []
        for item in items:
            if item.module_name in hidden_children:
                continue
            child_plugins = sorted(child_map.get(item.module_name, []))
            next_item = item
            if child_plugins:
                next_item = replace(item, child_plugins=child_plugins)
            collapsed.append(next_item)
        return collapsed

    def _resolve_parent_plugin_module(
        self,
        item: PluginCatalogItem,
        item_map: dict[str, PluginCatalogItem],
    ) -> str | None:
        if not item.is_loaded or item.is_explicit:
            return None

        parent_module = item.module_name.rpartition(".")[0]
        while parent_module:
            parent_item = item_map.get(parent_module)
            if parent_item is not None and parent_item.is_loaded:
                return parent_module
            parent_module = parent_module.rpartition(".")[0]
        return None

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
