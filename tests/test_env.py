from __future__ import annotations

import sys


def test_ensure_creates_directories(tmp_path, monkeypatch) -> None:
    from apeiria.env.ensure import ensure_apeiria_env

    monkeypatch.chdir(tmp_path)
    base = ensure_apeiria_env()
    assert base.is_dir()
    assert (base / "plugins").is_dir()
    assert (base / "pyproject.toml").is_file()
    assert (base / "plugins.yaml").is_file()


def test_ensure_idempotent(tmp_path, monkeypatch) -> None:
    from apeiria.env.ensure import ensure_apeiria_env

    monkeypatch.chdir(tmp_path)
    first = ensure_apeiria_env()
    second = ensure_apeiria_env()
    assert first == second


def test_find_uv() -> None:
    from apeiria.env.sync import _find_uv

    uv = _find_uv()
    assert uv is not None


def test_inject_apeiria_paths_does_not_load_from_toml(tmp_path, monkeypatch) -> None:
    import nonebot

    from apeiria.env.inject import inject_apeiria_paths

    monkeypatch.chdir(tmp_path)
    site_packages = (
        tmp_path / ".apeiria" / ".venv" / "lib" / "python3.12" / "site-packages"
    )
    site_packages.mkdir(parents=True)
    (tmp_path / ".apeiria" / "pyproject.toml").write_text(
        "[project]\nname = 'x'\n", encoding="utf-8"
    )

    def _fail(_path: object) -> None:
        msg = "load_from_toml should not be called"
        raise AssertionError(msg)

    monkeypatch.setattr(nonebot, "load_from_toml", _fail)

    inject_apeiria_paths()

    assert str(site_packages.resolve()) in sys.path
