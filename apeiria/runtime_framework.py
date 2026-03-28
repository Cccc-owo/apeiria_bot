from __future__ import annotations

import pkgutil
from pathlib import Path

import nonebot

FRAMEWORK_PLUGIN_MODULES = (
    "nonebot_plugin_apscheduler",
    "nonebot_plugin_localstore",
    "nonebot_plugin_orm",
    "nonebot_plugin_alconna",
    "apeiria.plugins.render",
)

FRAMEWORK_BUILTIN_PLUGIN_NAMES = ("echo",)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _official_plugin_root() -> Path:
    return _project_root() / "apeiria" / "plugins"


def _iter_official_plugin_modules() -> tuple[str, ...]:
    official_plugin_dir = _official_plugin_root().resolve()
    if not official_plugin_dir.is_dir():
        return ()

    discovered: list[str] = []
    for module_info in pkgutil.iter_modules([str(official_plugin_dir)]):
        if module_info.name.startswith("_"):
            continue
        discovered.append(f"apeiria.plugins.{module_info.name}")
    return tuple(sorted(discovered))


def load_framework() -> None:
    """Load framework plugins, builtins, and core side effects."""
    from apeiria.core.services.log import setup_logging

    setup_logging()

    nonebot.load_builtin_plugins(*FRAMEWORK_BUILTIN_PLUGIN_NAMES)
    for plugin in FRAMEWORK_PLUGIN_MODULES:
        nonebot.load_plugin(plugin)

    for plugin in _iter_official_plugin_modules():
        if plugin in FRAMEWORK_PLUGIN_MODULES:
            continue
        nonebot.load_plugin(plugin)

    import apeiria.core.hooks
    import apeiria.core.models  # noqa: F401
