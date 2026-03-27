"""Plugin store application service."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from apeiria.config.plugins import plugin_config_service
from apeiria.domains.plugins import plugin_catalog_service

from .models import StoreItemsPage, StoreItemsQuery, StorePluginItem, StoreSourceInfo
from .sources import OfficialNoneBotStoreSource, StoreSource


class PluginStoreService:
    """Read-only plugin store aggregation service."""

    def __init__(self, sources: list[StoreSource] | None = None) -> None:
        self._sources = sources or [OfficialNoneBotStoreSource()]

    def list_sources(self) -> list[StoreSourceInfo]:
        return [source.source_info() for source in self._sources]

    async def list_items(
        self,
        query: StoreItemsQuery | None = None,
    ) -> StoreItemsPage:
        effective_query = query or StoreItemsQuery()
        items = await self._collect_items(effective_query)
        total = len(items)
        per_page = max(1, min(effective_query.per_page, 100))
        page = max(1, effective_query.page)
        start = (page - 1) * per_page
        end = start + per_page
        return StoreItemsPage(
            items=items[start:end],
            total=total,
            page=page,
            per_page=per_page,
        )

    async def _collect_items(
        self,
        query: StoreItemsQuery,
    ) -> list[StorePluginItem]:
        loaded_plugins = await plugin_catalog_service.list_plugins()
        loaded_module_names = {item.module_name for item in loaded_plugins}

        project_config = plugin_config_service.read_project_plugin_config()
        registered_module_names = set(project_config["modules"])
        package_bindings = project_config["packages"]
        module_to_package = {
            module_name: package_name
            for package_name, module_names in package_bindings.items()
            for module_name in module_names
        }

        items: list[StorePluginItem] = []
        for source in self._sources:
            if (
                query.source_id
                and source.source_info().source_id != query.source_id
            ):
                continue
            for item in await source.list_items():
                installed = (
                    item.module_name in loaded_module_names
                    or item.module_name in registered_module_names
                )
                registered = item.module_name in registered_module_names
                installed_package = module_to_package.get(item.module_name)
                normalized = replace(
                    item,
                    is_installed=installed,
                    is_registered=registered,
                    installed_package=installed_package,
                    installed_module_names=package_bindings.get(
                        installed_package or "",
                        [],
                    ),
                )
                if _match_item(normalized, query):
                    items.append(normalized)

        items.sort(
            key=_item_sort_key(query.sort)
        )
        return items

    async def get_item(
        self,
        *,
        source_id: str,
        plugin_id: str,
    ) -> StorePluginItem | None:
        items = await self._collect_items(StoreItemsQuery(source_id=source_id))
        for item in items:
            if item.plugin_id == plugin_id:
                return item
        return None


def _match_item(item: StorePluginItem, query: StoreItemsQuery) -> bool:
    if query.installed_only and not item.is_installed:
        return False
    if query.uninstalled_only and item.is_installed:
        return False
    if query.category and query.category not in item.tags:
        return False

    keyword = query.search.strip().lower()
    if not keyword:
        return True

    haystack = " ".join(
        [
            item.name,
            item.module_name,
            item.package_name,
            item.description or "",
            item.author or "",
            " ".join(item.tags),
        ]
    ).lower()
    return keyword in haystack


def _item_sort_key(sort_mode: str):
    if sort_mode == "name":
        return lambda item: (
            item.name.lower(),
            item.module_name.lower(),
        )
    if sort_mode == "updated":
        return lambda item: (
            -_timestamp_value(item.publish_time),
            item.name.lower(),
            item.module_name.lower(),
        )
    return lambda item: (
        not item.is_installed,
        not item.is_official,
        item.name.lower(),
        item.module_name.lower(),
    )


def _timestamp_value(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return int(datetime.fromisoformat(normalized).timestamp())
    except ValueError:
        return 0


plugin_store_service = PluginStoreService()
