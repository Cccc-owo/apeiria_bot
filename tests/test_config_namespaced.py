from __future__ import annotations

import os
from types import SimpleNamespace


def _isolate_env(monkeypatch) -> None:
    monkeypatch.setattr(os, "environ", dict(os.environ))


def test_expand_config_flat_help_env(monkeypatch) -> None:
    from apeiria.config.loader import expand_config
    from apeiria.config.models import AppConfig

    _isolate_env(monkeypatch)
    for key in ("EXPAND_COMMANDS", "HIDDEN_PLUGINS", "TITLE", "SUBTITLE"):
        os.environ.pop(key, None)

    app = AppConfig(
        plugins={"help": {"expand_commands": True, "hidden_plugins": ["x"]}}
    )
    expand_config(app)

    assert os.environ["EXPAND_COMMANDS"] == "1"
    assert os.environ["HIDDEN_PLUGINS"] == '["x"]'
    assert not any(key.startswith("HELP__") for key in os.environ)


def test_expand_config_enabled_aliases_no_collision(monkeypatch) -> None:
    from apeiria.config.loader import expand_config
    from apeiria.config.models import AppConfig

    _isolate_env(monkeypatch)
    for key in ("ENABLED", "TRIGGER_REPLY__ENABLED", "FRIENDSHIP__ENABLED"):
        os.environ.pop(key, None)

    app = AppConfig(
        plugins={
            "trigger_reply": {"enabled": False},
            "friendship": {"enabled": True},
        }
    )
    expand_config(app)

    assert "ENABLED" not in os.environ
    assert os.environ["TRIGGER_REPLY__ENABLED"] == "0"
    assert os.environ["FRIENDSHIP__ENABLED"] == "1"


def test_update_runtime_config_sets_aliased_driver_attrs(monkeypatch) -> None:
    from apeiria.config.loader import update_runtime_config
    from apeiria.config.models import AppConfig

    _isolate_env(monkeypatch)
    fake_config = SimpleNamespace()
    monkeypatch.setattr(
        "nonebot.get_driver", lambda: SimpleNamespace(config=fake_config)
    )

    app = AppConfig(
        plugins={
            "trigger_reply": {"enabled": False},
            "friendship": {"enabled": True},
        }
    )
    update_runtime_config(app)

    assert fake_config.trigger_reply__enabled is False
    assert fake_config.friendship__enabled is True
