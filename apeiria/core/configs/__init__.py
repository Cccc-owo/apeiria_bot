from __future__ import annotations

from .models import PluginExtraData, PluginType, RegisterConfig
from .registry import (
    configs_from_model,
    get_registered_plugin_config,
    iter_registered_plugin_configs,
    register_plugin_config,
)

__all__ = [
    "BotConfig",
    "PluginExtraData",
    "PluginType",
    "RegisterConfig",
    "bot_config",
    "configs_from_model",
    "get_registered_plugin_config",
    "iter_registered_plugin_configs",
    "register_plugin_config",
]


def __getattr__(name: str) -> object:
    if name in {"BotConfig", "bot_config"}:
        from .config import BotConfig, bot_config

        exports = {
            "BotConfig": BotConfig,
            "bot_config": bot_config,
        }
        return exports[name]
    raise AttributeError(name)
