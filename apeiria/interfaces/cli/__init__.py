"""CLI interface package."""

from .adapter_commands import adapter
from .driver_commands import driver
from .env_commands import check, env, init, repair, run, status
from .main import cli, main
from .plugin_commands import plugin
from .resource_commands import adapter as adapter_resource
from .resource_commands import driver as driver_resource
from .resource_commands import plugin as plugin_resource
from .webui_commands import webui

__all__ = [
    "adapter",
    "adapter_resource",
    "check",
    "cli",
    "driver",
    "driver_resource",
    "env",
    "init",
    "main",
    "plugin",
    "plugin_resource",
    "repair",
    "run",
    "status",
    "webui",
]
