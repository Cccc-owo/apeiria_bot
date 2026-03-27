"""Plugin store source adapters."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import replace
from datetime import UTC, datetime

from apeiria.cli_nb import search_store_packages_async

from .models import StorePluginItem, StoreSourceInfo


class StoreSource(ABC):
    """Abstract store source."""

    @abstractmethod
    def source_info(self) -> StoreSourceInfo:
        """Return source metadata."""

    @abstractmethod
    async def list_items(self) -> list[StorePluginItem]:
        """Return normalized store items."""


class OfficialNoneBotStoreSource(StoreSource):
    """Official NoneBot plugin source."""

    def __init__(self) -> None:
        self._last_synced_at = ""
        self._last_error = ""

    def source_info(self) -> StoreSourceInfo:
        return StoreSourceInfo(
            source_id="official-nonebot",
            name="NoneBot2源",
            kind="official-nonebot",
            enabled=True,
            is_builtin=True,
            is_official=True,
            base_url="https://nonebot.dev/store/plugins",
            last_synced_at=self._last_synced_at or None,
            last_error=self._last_error or None,
        )

    async def list_items(self) -> list[StorePluginItem]:
        try:
            items = await search_store_packages_async("plugin")
        except Exception as exc:
            self._last_error = str(exc)
            raise

        now = datetime.now(UTC).isoformat()
        self._last_synced_at = now
        self._last_error = ""
        source = replace(self.source_info(), last_synced_at=now, last_error=None)
        normalized: list[StorePluginItem] = []
        for item in items:
            normalized_item = _normalize_store_item(item, source)
            if normalized_item is not None:
                normalized.append(normalized_item)
        return normalized


class JsonHttpStoreSource(StoreSource):
    """Reserved adapter for future custom HTTP JSON sources."""

    def __init__(self, source_id: str, name: str, base_url: str) -> None:
        self._source = StoreSourceInfo(
            source_id=source_id,
            name=name,
            kind="json-http",
            enabled=True,
            is_builtin=False,
            is_official=False,
            base_url=base_url,
        )

    def source_info(self) -> StoreSourceInfo:
        return self._source

    async def list_items(self) -> list[StorePluginItem]:
        raise NotImplementedError("json-http custom sources are not implemented yet")


def _normalize_store_item(
    item: object,
    source: StoreSourceInfo,
) -> StorePluginItem | None:
    module_name = _read_str_attr(item, "module_name")
    package_name = _read_package_name(item)
    name = _read_str_attr(item, "name") or module_name or package_name
    if not module_name or not package_name or not name:
        return None

    description = (
        _read_str_attr(item, "desc")
        or _read_str_attr(item, "description")
        or _read_str_attr(item, "summary")
        or None
    )
    raw_project_link = _read_str_attr(item, "project_link")
    homepage = _normalize_external_url(_read_str_attr(item, "homepage"))
    project_link = _normalize_external_url(raw_project_link) or homepage
    author = _read_str_attr(item, "author") or None
    author_link = _read_author_link(item)
    version = (
        _read_str_attr(item, "latest_version")
        or _read_str_attr(item, "version")
        or None
    )
    tags = _read_tags(item)
    extra = _read_extra(item)

    return StorePluginItem(
        source_id=source.source_id,
        source_name=source.name,
        plugin_id=module_name,
        name=name,
        module_name=module_name,
        package_name=package_name,
        description=description,
        project_link=project_link,
        homepage=homepage,
        author=author,
        author_link=author_link,
        version=version,
        tags=tags,
        is_official=source.is_official,
        extra=extra,
    )


def _read_package_name(item: object) -> str:
    project_link = _read_str_attr(item, "project_link")
    if project_link:
        return project_link

    as_dependency = getattr(item, "as_dependency", None)
    if callable(as_dependency):
        dependency = as_dependency()
        if isinstance(dependency, str) and dependency.strip():
            return dependency.strip()
    return ""


def _read_tags(item: object) -> list[str]:
    raw = getattr(item, "tags", None)
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    for tag in raw:
        parsed = _normalize_tag(str(tag))
        if parsed:
            normalized.append(parsed)
    return normalized


def _read_author_link(item: object) -> str | None:
    for attr in ("author_link", "author_url", "author_homepage", "author_repo"):
        value = _normalize_external_url(_read_str_attr(item, attr))
        if value is not None:
            return value
    return None


def _read_extra(item: object) -> dict[str, object]:
    keys = getattr(item, "__dict__", {})
    if not isinstance(keys, dict):
        return {}
    excluded = {
        "name",
        "module_name",
        "project_link",
        "desc",
        "description",
        "summary",
        "author",
        "homepage",
        "latest_version",
        "version",
        "tags",
    }
    return {
        key: value
        for key, value in keys.items()
        if key not in excluded and value is not None
    }


def _read_str_attr(item: object, attr: str) -> str:
    value = getattr(item, attr, "")
    return value.strip() if isinstance(value, str) else ""


def _normalize_external_url(value: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.startswith(("http://", "https://")):
        return normalized
    return None


def _normalize_tag(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""

    label_match = re.search(r"label=(['\"])(.*?)\1", normalized)
    if label_match:
        return label_match.group(2).strip()

    if " color=" in normalized:
        normalized = normalized.split(" color=", 1)[0].strip()
    if normalized.startswith("label="):
        normalized = normalized[6:].strip().strip("'\"")
    return normalized
