from __future__ import annotations

import nonebot

from apeiria.plugin_config_bootstrap import bootstrap_plugin_configs
from apeiria.runtime import load_framework
from apeiria.user_config import get_project_config_kwargs, read_env_config
from apeiria.user_drivers import get_project_driver_kwargs
from apeiria.user_plugin_env import inject_plugin_site_packages
from apeiria.user_runtime import load_user_plugins, load_user_setup

bootstrap_plugin_configs()
inject_plugin_site_packages()
config_kwargs = get_project_config_kwargs()
project_driver_kwargs = get_project_driver_kwargs()

# Driver priority: apeiria.drivers.toml > apeiria.config.toml > env
if project_driver_kwargs.get("driver"):
    # drivers.toml has driver, remove driver from config_kwargs if present
    config_kwargs.pop("driver", None)
    driver_kwargs = project_driver_kwargs
elif "driver" in config_kwargs:
    # config.toml has driver, use it
    driver_kwargs = {}
else:
    # Neither has driver, try env
    env_config = read_env_config()
    driver_kwargs = {"driver": env_config["driver"]} if env_config.get("driver") else {}

nonebot.init(**config_kwargs, **driver_kwargs)
nonebot.load_from_toml("pyproject.toml")

load_user_setup()
load_framework()
load_user_plugins()

if __name__ == "__main__":
    nonebot.run()
