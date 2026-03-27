"""Plugin store models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StoreSourceInfo:
    """One plugin store source exposed to callers."""

    source_id: str
    name: str
    kind: str
    enabled: bool = True
    is_builtin: bool = False
    is_official: bool = False
    base_url: str | None = None
    last_synced_at: str | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class StorePluginItem:
    """Normalized plugin store item."""

    source_id: str
    source_name: str
    plugin_id: str
    name: str
    module_name: str
    package_name: str
    description: str | None = None
    project_link: str | None = None
    homepage: str | None = None
    author: str | None = None
    author_link: str | None = None
    version: str | None = None
    tags: list[str] = field(default_factory=list)
    is_official: bool = False
    publish_time: str | None = None
    extra: dict[str, object] = field(default_factory=dict)
    is_installed: bool = False
    is_registered: bool = False
    installed_package: str | None = None
    installed_module_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StoreItemsQuery:
    """Read-only store item query."""

    source_id: str = ""
    search: str = ""
    category: str = ""
    sort: str = "default"
    installed_only: bool = False
    uninstalled_only: bool = False
    page: int = 1
    per_page: int = 16


@dataclass(frozen=True)
class StoreItemsPage:
    """Paginated store item result."""

    items: list[StorePluginItem]
    total: int
    page: int
    per_page: int


@dataclass(frozen=True)
class PluginStoreInstallRequest:
    """Request to install one plugin from the store."""

    source_id: str
    plugin_id: str
    package_name: str
    module_name: str


@dataclass(frozen=True)
class PluginStoreTask:
    """One plugin store background task."""

    task_id: str
    title: str
    status: str
    logs: str
    error: str | None = None
    result: dict[str, object] = field(default_factory=dict)
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
