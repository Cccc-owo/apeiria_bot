"""Build and cache plugin dependency graphs."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nonebot.plugin.model import Plugin


@dataclass
class DepGraph:
    """Directed plugin dependency graph with its reverse and nesting edges."""

    graph: dict[str, set[str]] = field(default_factory=dict)
    reverse: dict[str, set[str]] = field(default_factory=dict)
    nesting: set[tuple[str, str]] = field(default_factory=set)


class _Cache:
    """Hold the cached dependency graph across calls."""

    value: DepGraph | None = None


_runtime_edges: set[tuple[str, str]] = set()


def record_dependency(plugin_name: str, dep_name: str) -> None:
    """Record a runtime dependency discovered through ``require()``."""
    _runtime_edges.add((plugin_name, dep_name))


def reset_dependency_graph() -> None:
    """Clear runtime edges and cached graph (mainly for tests)."""
    _runtime_edges.clear()
    _Cache.value = None


def build_dependency_graph(plugins: Collection["Plugin"]) -> DepGraph:
    """Build a dependency graph from plugins and runtime edges.

    Args:
        plugins: The collection of NoneBot plugins to include.

    Returns:
        A :class:`DepGraph` containing forward, reverse, and nesting edges.
    """
    graph: dict[str, set[str]] = {}
    nesting: set[tuple[str, str]] = set()

    for plugin in plugins:
        graph.setdefault(plugin.name, set())
        for sub in plugin.sub_plugins:
            graph.setdefault(plugin.name, set()).add(sub.name)
            nesting.add((plugin.name, sub.name))

    for src, dst in _runtime_edges:
        graph.setdefault(src, set()).add(dst)
        graph.setdefault(dst, set())

    reverse: dict[str, set[str]] = {}
    for node, deps in graph.items():
        reverse.setdefault(node, set())
        for dep in deps:
            reverse.setdefault(dep, set()).add(node)

    return DepGraph(graph=graph, reverse=reverse, nesting=nesting)


def get_cached_graph(plugins: Collection["Plugin"]) -> DepGraph:
    """Return the cached dependency graph, building it if needed.

    Args:
        plugins: The collection of NoneBot plugins to include.

    Returns:
        The cached :class:`DepGraph`.
    """
    if _Cache.value is None:
        _Cache.value = build_dependency_graph(plugins)
    return _Cache.value
