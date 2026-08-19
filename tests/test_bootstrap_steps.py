from __future__ import annotations


def test_step_load_pypi_loads_enabled_packages_by_module(tmp_path, monkeypatch) -> None:
    import nonebot

    from apeiria.bootstrap import steps

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".apeiria").mkdir()
    (tmp_path / ".apeiria" / "plugins.yaml").write_text(
        "dirs: []\n"
        "packages:\n"
        "  服务器状态查看: nonebot-plugin-status>=0.9.0\n"
        "  关闭项: nonebot-plugin-foo\n"
        "states:\n"
        "  关闭项:\n"
        "    enabled: false\n",
        encoding="utf-8",
    )

    loaded: list[str] = []

    def _fake_load_plugin(module: str) -> None:
        loaded.append(module)

    monkeypatch.setattr(nonebot, "load_plugin", _fake_load_plugin)

    steps.step_load_pypi()

    assert loaded == ["nonebot_plugin_status"]


def test_step_load_builtins_uses_scan_plugins_and_respects_disabled(
    tmp_path, monkeypatch
) -> None:
    import nonebot

    from apeiria.bootstrap import steps

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".apeiria").mkdir()
    (tmp_path / ".apeiria" / "plugins.yaml").write_text(
        "dirs: []\npackages: {}\nstates:\n  admin:\n    enabled: false\n",
        encoding="utf-8",
    )

    loaded: list[str] = []
    monkeypatch.setattr(nonebot, "load_plugin", loaded.append)

    steps.step_load_builtins()

    assert "apeiria.builtin_plugins.admin" not in loaded
    assert "apeiria.builtin_plugins.help" in loaded


def test_step_require_tracker_patches_require_entries(monkeypatch) -> None:
    import nonebot
    from nonebot.plugin import load as plugin_load

    from apeiria.bootstrap import steps

    monkeypatch.setattr(steps, "_require_tracker_installed", False)
    monkeypatch.setattr(nonebot, "require", nonebot.require)
    monkeypatch.setattr(nonebot.plugin, "require", nonebot.plugin.require)
    monkeypatch.setattr(plugin_load, "require", plugin_load.require)

    original_nb = nonebot.require
    steps.step_require_tracker()

    assert nonebot.require is not original_nb
    assert nonebot.plugin.require is nonebot.require
    assert plugin_load.require is nonebot.require

    current = nonebot.require
    steps.step_require_tracker()
    assert nonebot.require is current


def test_step_require_tracker_records_runtime_dependency(monkeypatch) -> None:
    from types import ModuleType, SimpleNamespace

    import nonebot
    from nonebot.plugin import load as plugin_load

    from apeiria.bootstrap import steps
    from apeiria.plugin import dependency_graph

    monkeypatch.setattr(steps, "_require_tracker_installed", False)
    monkeypatch.setattr(nonebot, "require", nonebot.require)
    monkeypatch.setattr(nonebot.plugin, "require", nonebot.plugin.require)
    monkeypatch.setattr(plugin_load, "require", plugin_load.require)

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        dependency_graph,
        "record_dependency",
        lambda a, b: calls.append((a, b)),
    )

    def _fake_require(_name: str) -> ModuleType:
        return ModuleType(_name)

    monkeypatch.setattr(plugin_load, "require", _fake_require)

    current = SimpleNamespace(name="foo")
    dep = SimpleNamespace(name="dep")

    monkeypatch.setattr(
        nonebot.plugin,
        "get_plugin_by_module_name",
        lambda module_name: current if module_name == "plugins.foo" else None,
    )
    monkeypatch.setattr(
        nonebot.plugin,
        "get_plugin",
        lambda name: dep if name == "dep" else None,
    )

    steps.step_require_tracker()

    tracking = nonebot.require
    exec(
        "require('dep')",
        {"__name__": "plugins.foo", "require": tracking},
    )

    assert calls == [("foo", "dep")]


def test_resolve_frontend_file_serves_within_root(tmp_path) -> None:
    from apeiria.bootstrap.steps import _resolve_frontend_file

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("index", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("app", encoding="utf-8")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    assert _resolve_frontend_file(dist, "assets/app.js").read_text() == "app"
    assert _resolve_frontend_file(dist, "dashboard").read_text() == "index"
    assert _resolve_frontend_file(dist, "../secret.txt") is None
    assert _resolve_frontend_file(dist, "/etc/passwd") is None
