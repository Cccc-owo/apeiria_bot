"""Common utility functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nonebot.plugin import Plugin

from apeiria.core.configs.models import PluginExtraData


def get_plugin_extra(plugin: Plugin) -> PluginExtraData | None:
    """Extract PluginExtraData from a loaded plugin.

    Returns None for third-party plugins without our metadata format.
    """
    if plugin.metadata and plugin.metadata.extra:
        return PluginExtraData.from_extra(plugin.metadata.extra)
    return None


def get_plugin_name(plugin: Plugin) -> str:
    """Get display name of a plugin."""
    if plugin.metadata and plugin.metadata.name:
        return plugin.metadata.name
    return plugin.name


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration string."""
    if seconds <= 0:
        return "永久"
    parts: list[str] = []
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分钟")
    if seconds:
        parts.append(f"{seconds}秒")
    return "".join(parts) or "0秒"


def safe_json_loads(text: str | None, default: Any = None) -> Any:
    """Safely parse JSON string, returning default on failure."""
    if not text:
        return default if default is not None else []
    import json

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []
