from __future__ import annotations

"""Top-level NoneBot bootstrap used by bot.py and CLI entrypoints."""

from typing import Any, cast

import nonebot

from apeiria.config import driver_config_service, project_config_service
from apeiria.plugin_config_bootstrap import bootstrap_plugin_configs
from apeiria.runtime_env import (
    inject_plugin_site_packages,
    process_pending_plugin_module_uninstalls,
    process_pending_plugin_requirement_removals,
)
from apeiria.runtime_framework import load_framework
from apeiria.runtime_user import load_user_plugins, load_user_setup


def resolve_driver_kwargs(config_kwargs: dict[str, object]) -> dict[str, object]:
    """Resolve driver kwargs with the runtime precedence used by the project.

    Project-managed driver config wins over values loaded from config files.
    If the project does not pin a driver, fall back to env-derived config so
    existing NoneBot behavior remains intact.
    """
    project_driver_kwargs = driver_config_service.get_project_driver_kwargs()

    if project_driver_kwargs.get("driver"):
        config_kwargs.pop("driver", None)
        return cast("dict[str, object]", project_driver_kwargs)
    if "driver" in config_kwargs:
        return {}

    env_config = project_config_service.read_env_config()
    env_driver = env_config.get("driver")
    if isinstance(env_driver, str) and env_driver:
        return {"driver": env_driver}
    return {}


def initialize_nonebot() -> None:
    """Initialize NoneBot and load all project-managed runtime layers.

    The order matters:
    1. bootstrap plugin config metadata
    2. process deferred plugin package removals
    3. clear deferred plugin module removals after restart
    4. expose extension environment site-packages
    3. initialize NoneBot with merged config
    4. load local user setup, framework plugins, then project plugins
    """
    bootstrap_plugin_configs()
    process_pending_plugin_requirement_removals()
    process_pending_plugin_module_uninstalls()
    inject_plugin_site_packages()

    config_kwargs = project_config_service.get_project_config_kwargs()
    driver_kwargs = resolve_driver_kwargs(config_kwargs)

    nonebot.init(
        **cast("dict[str, Any]", config_kwargs),
        **cast("dict[str, Any]", driver_kwargs),
    )
    nonebot.load_from_toml("pyproject.toml")

    load_user_setup()
    load_framework()
    load_user_plugins()


def run() -> None:
    """Convenience entrypoint for CLI-style execution."""
    initialize_nonebot()
    nonebot.run()
