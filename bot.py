from __future__ import annotations

import nonebot

from apeiria.plugin_config_bootstrap import bootstrap_plugin_configs
from apeiria.runtime import load_framework
from apeiria.user_config import get_project_config_kwargs
from apeiria.user_drivers import get_project_driver_kwargs
from apeiria.user_runtime import load_user_plugins, load_user_setup

bootstrap_plugin_configs()
nonebot.init(**get_project_config_kwargs(), **get_project_driver_kwargs())
nonebot.load_from_toml("pyproject.toml")

load_user_setup()
load_framework()
load_user_plugins()

if __name__ == "__main__":
    nonebot.run()
