"""Generate help data from loaded plugins."""

from __future__ import annotations

from dataclasses import dataclass

import nonebot

from apeiria.core.configs.models import PluginType
from apeiria.core.utils.helpers import get_plugin_extra, get_plugin_name


@dataclass
class PluginHelpInfo:
    """Help information for a single plugin."""

    module_name: str
    name: str
    description: str
    usage: str
    plugin_type: str
    admin_level: int
    commands: list[str]
    version: str


def generate_help_list(
    _user_id: str = "",
    _group_id: str | None = None,
) -> list[PluginHelpInfo]:
    """Generate help list from all loaded plugins.

    user_id and group_id reserved for future permission filtering.
    """
    plugins = nonebot.get_loaded_plugins()
    result: list[PluginHelpInfo] = []

    for plugin in plugins:
        meta = plugin.metadata
        extra = get_plugin_extra(plugin)

        if extra and extra.plugin_type in (PluginType.HIDDEN, PluginType.PARENT):
            continue
        if not meta:
            continue

        result.append(
            PluginHelpInfo(
                module_name=plugin.module_name,
                name=get_plugin_name(plugin),
                description=meta.description or "",
                usage=meta.usage or "",
                plugin_type=extra.plugin_type.value if extra else "normal",
                admin_level=extra.admin_level if extra else 0,
                commands=extra.commands if extra else [],
                version=extra.version if extra else "",
            )
        )

    result.sort(key=lambda p: (p.admin_level, p.name))
    return result


def find_plugin_by_name(name: str) -> PluginHelpInfo | None:
    """Find a plugin by display name or module name."""
    all_plugins = generate_help_list()
    name_lower = name.lower()
    for p in all_plugins:
        if p.name.lower() == name_lower or p.module_name.lower() == name_lower:
            return p
    for p in all_plugins:
        if name_lower in p.name.lower() or name_lower in p.module_name.lower():
            return p
    return None
