"""Common utility functions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nonebot.plugin import Plugin

import nonebot

from apeiria.core.configs.models import PluginExtraData
from apeiria.core.i18n import t
from apeiria.core.plugin_policy import is_framework_protected_plugin_module

OFFICIAL_PLUGIN_ROOT = (Path(__file__).resolve().parents[2] / "plugins").resolve()
CUSTOM_PLUGIN_ROOT = (Path(__file__).resolve().parents[3] / "local_plugins").resolve()


def get_plugin_extra(plugin: Plugin) -> PluginExtraData | None:
    """Extract PluginExtraData from a loaded plugin."""
    if plugin.metadata and plugin.metadata.extra:
        return PluginExtraData.from_extra(plugin.metadata.extra)
    return None


def get_plugin_name(plugin: Plugin) -> str:
    """Get display name of a plugin."""
    if plugin.metadata and plugin.metadata.name:
        return plugin.metadata.name
    return plugin.name


def get_plugin_required_plugins(plugin: Plugin) -> list[str]:
    """Get declared plugin dependencies from metadata."""
    extra = get_plugin_extra(plugin)
    if not extra:
        return []
    return [
        module
        for module in extra.required_plugins
        if isinstance(module, str) and module
    ]


def find_loaded_plugin(name: str) -> Plugin | None:
    """Find loaded plugin by module name or display name."""
    for plugin in nonebot.get_loaded_plugins():
        if plugin.module_name == name or get_plugin_name(plugin) == name:
            return plugin
    return None


def get_plugin_dependents(module_name: str) -> list[str]:
    """Get loaded plugins that depend on the target plugin."""
    dependents = {
        get_plugin_name(plugin)
        for plugin in nonebot.get_loaded_plugins()
        if module_name in get_plugin_required_plugins(plugin)
    }
    return sorted(dependents)


def get_plugin_source(plugin: Plugin) -> str:
    """Classify plugin source for management UI."""
    module = getattr(plugin, "module", None)
    module_file = getattr(module, "__file__", None)
    if module_file:
        try:
            resolved = Path(module_file).resolve()
        except OSError:
            resolved = None
        if resolved:
            if OFFICIAL_PLUGIN_ROOT in resolved.parents:
                return "official"
            if CUSTOM_PLUGIN_ROOT in resolved.parents:
                return "custom"

    if is_framework_protected_plugin_module(plugin.module_name):
        return "framework"
    if plugin.module_name in {"echo", "nonebot.plugins.echo"}:
        return "builtin"
    return "external"


def get_plugin_protection_reason(module_name: str) -> str | None:
    """Return human-readable reason when a plugin should not be disabled."""
    reasons: list[str] = []
    if is_framework_protected_plugin_module(module_name):
        reasons.append(t("common.framework_required"))

    dependents = get_plugin_dependents(module_name)
    if dependents:
        reasons.append(t("common.required_by_plugins", plugins=", ".join(dependents)))

    return "；".join(reasons) if reasons else None


def is_plugin_protected(module_name: str) -> bool:
    """Check whether a plugin is protected from being disabled."""
    return get_plugin_protection_reason(module_name) is not None


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration string."""
    from apeiria.core.i18n import t

    if seconds <= 0:
        return t("duration.permanent")
    parts: list[str] = []
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        parts.append(f"{days}{t('duration.day')}")
    if hours:
        parts.append(f"{hours}{t('duration.hour')}")
    if minutes:
        parts.append(f"{minutes}{t('duration.minute')}")
    if seconds:
        parts.append(f"{seconds}{t('duration.second')}")
    return "".join(parts) or t("duration.zero")


def safe_json_loads(text: str | None, default: Any = None) -> Any:
    """Safely parse JSON string, returning default on failure."""
    if not text:
        return default if default is not None else []
    import json

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []
