from __future__ import annotations

from types import ModuleType
from unittest.mock import MagicMock

import pytest

from apeiria.plugin.dependency_graph import (
    build_dependency_graph,
    record_dependency,
    reset_dependency_graph,
)


def _make_module(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__name__ = name
    return mod


def _make_plugin(
    name: str,
    module: ModuleType,
    metadata=None,
    sub_plugins: set | None = None,
    parent=None,
):
    from nonebot.plugin.model import Plugin

    return Plugin(
        name=name,
        module=module,
        module_name=module.__name__,
        manager=MagicMock(),
        metadata=metadata,
        sub_plugins=sub_plugins or set(),
        parent_plugin=parent,
    )


@pytest.fixture(autouse=True)
def _clean_runtime_edges():
    reset_dependency_graph()
    yield
    reset_dependency_graph()


def test_recorded_require_edges_are_used() -> None:
    record_dependency("plugin_a", "dep_a")
    a = _make_plugin("plugin_a", _make_module("plugin_a"))
    b = _make_plugin("dep_a", _make_module("dep_a"))

    graph = build_dependency_graph([a, b])

    assert graph.graph["plugin_a"] == {"dep_a"}
    assert graph.reverse["dep_a"] == {"plugin_a"}


def test_multiple_recorded_edges() -> None:
    record_dependency("plugin_a", "dep_a")
    record_dependency("plugin_a", "dep_b")
    a = _make_plugin("plugin_a", _make_module("plugin_a"))

    graph = build_dependency_graph([a])

    assert graph.graph["plugin_a"] == {"dep_a", "dep_b"}
    assert graph.reverse["dep_a"] == {"plugin_a"}
    assert graph.reverse["dep_b"] == {"plugin_a"}


def test_no_recorded_edges_keeps_loaded_plugin_keys() -> None:
    a = _make_plugin("plugin_a", _make_module("plugin_a"))

    graph = build_dependency_graph([a])

    assert graph.graph["plugin_a"] == set()
    assert graph.reverse == {"plugin_a": set()}


def test_nesting_still_creates_edges() -> None:
    child = _make_plugin("child", _make_module("parent.child"))
    parent = _make_plugin("parent", _make_module("parent"), sub_plugins={child})

    graph = build_dependency_graph([parent, child])

    assert "child" in graph.graph["parent"]
    assert "parent" in graph.reverse["child"]
    assert ("parent", "child") in graph.nesting


def test_get_cached_graph_uses_runtime_edges() -> None:
    from apeiria.plugin.dependency_graph import get_cached_graph

    record_dependency("plugin_a", "dep_a")
    a = _make_plugin("plugin_a", _make_module("plugin_a"))
    b = _make_plugin("dep_a", _make_module("dep_a"))

    graph = get_cached_graph([a, b])

    assert graph.graph["plugin_a"] == {"dep_a"}
