from __future__ import annotations

from pathlib import Path

import nonebot

FRAMEWORK_PLUGIN_MODULES = (
    "nonebot_plugin_sentry",
    "nonebot_plugin_apscheduler",
    "nonebot_plugin_localstore",
    "nonebot_plugin_orm",
    "nonebot_plugin_alconna",
    "nonebot_plugin_htmlkit",
)

FRAMEWORK_BUILTIN_PLUGIN_NAMES = ("echo",)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _official_plugin_root() -> Path:
    return _project_root() / "apeiria" / "plugins"


def load_framework() -> None:
    """Load framework plugins, builtins, and core side effects."""
    from apeiria.core.services.log import setup_logging

    setup_logging()

    nonebot.load_builtin_plugins(*FRAMEWORK_BUILTIN_PLUGIN_NAMES)
    for plugin in FRAMEWORK_PLUGIN_MODULES:
        nonebot.load_plugin(plugin)

    official_plugin_dir = _official_plugin_root().resolve()
    if official_plugin_dir.is_dir():
        nonebot.load_plugins(str(official_plugin_dir))

    import apeiria.core.hooks
    import apeiria.core.models  # noqa: F401
