from __future__ import annotations

import sys


def _write_plugins_yaml(tmp_path, dirs: list[str], states: dict | None = None) -> None:
    (tmp_path / ".apeiria").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".apeiria" / "plugins.yaml").write_text(
        "dirs:\n"
        + "".join(f"  - {d!r}\n" for d in dirs)
        + "packages: {}\n"
        + f"states: {states or {}}\n",
        encoding="utf-8",
    )


def _make_plugin(path, name: str) -> None:
    plugin_dir = path / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "__init__.py").write_text("", encoding="utf-8")


def test_step_load_local_loads_default_dir_plugin(tmp_path, monkeypatch) -> None:
    import nonebot

    from apeiria.bootstrap import steps

    monkeypatch.chdir(tmp_path)
    _write_plugins_yaml(tmp_path, [".apeiria/plugins"])
    _make_plugin(tmp_path / ".apeiria" / "plugins", "foo")

    loaded: list[str] = []
    monkeypatch.setattr(nonebot, "load_plugin", loaded.append)

    steps.step_load_local()

    assert loaded == ["plugins.foo"]


def test_step_load_local_skips_disabled_plugin(tmp_path, monkeypatch) -> None:
    import nonebot

    from apeiria.bootstrap import steps

    monkeypatch.chdir(tmp_path)
    _write_plugins_yaml(
        tmp_path,
        [".apeiria/plugins"],
        states={"foo": {"enabled": False}},
    )
    _make_plugin(tmp_path / ".apeiria" / "plugins", "foo")

    loaded: list[str] = []
    monkeypatch.setattr(nonebot, "load_plugin", loaded.append)

    steps.step_load_local()

    assert loaded == []


def test_step_load_local_supports_custom_dir(tmp_path, monkeypatch) -> None:
    import nonebot

    from apeiria.bootstrap import steps

    monkeypatch.chdir(tmp_path)
    _write_plugins_yaml(tmp_path, ["custom/plugins"])
    _make_plugin(tmp_path / "custom" / "plugins", "bar")

    loaded: list[str] = []
    monkeypatch.setattr(nonebot, "load_plugin", loaded.append)

    steps.step_load_local()

    assert loaded == ["plugins.bar"]
    assert str((tmp_path / "custom").resolve()) in sys.path


def test_step_load_local_skips_invalid_directory_name(tmp_path, monkeypatch) -> None:
    import nonebot

    from apeiria.bootstrap import steps

    monkeypatch.chdir(tmp_path)
    _write_plugins_yaml(tmp_path, [".apeiria/plugins"])
    _make_plugin(tmp_path / ".apeiria" / "plugins", "foo-bar")

    loaded: list[str] = []
    monkeypatch.setattr(nonebot, "load_plugin", loaded.append)

    steps.step_load_local()

    assert loaded == []


def test_step_load_local_tolerates_duplicate_module(tmp_path, monkeypatch) -> None:
    import nonebot

    from apeiria.bootstrap import steps

    monkeypatch.chdir(tmp_path)
    _write_plugins_yaml(tmp_path, ["a/plugins", "b/plugins"])
    _make_plugin(tmp_path / "a" / "plugins", "dup")
    _make_plugin(tmp_path / "b" / "plugins", "dup")

    calls: list[str] = []
    real_append = calls.append

    def _fake_load_plugin(module: str) -> None:
        if module in calls:
            msg = f"Plugin already exists: {module}"
            raise RuntimeError(msg)
        real_append(module)

    monkeypatch.setattr(nonebot, "load_plugin", _fake_load_plugin)

    steps.step_load_local()

    assert calls == ["plugins.dup"]


def test_local_plugin_module_name() -> None:
    from pathlib import Path

    from apeiria.plugin.scanner import local_plugin_module_name

    assert local_plugin_module_name(Path(".apeiria/plugins/foo")) == "plugins.foo"
    assert local_plugin_module_name(Path("custom/plugins/bar")) == "plugins.bar"
    assert local_plugin_module_name(Path(".apeiria/plugins/foo-bar")) is None
    assert local_plugin_module_name(Path("some-dir/foo")) is None
