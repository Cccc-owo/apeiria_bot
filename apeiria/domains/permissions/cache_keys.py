"""Cache key helpers for permission-related state."""

from __future__ import annotations


def user_level_cache_key(user_id: str, group_id: str) -> str:
    """Return the cache key for one user's level in one group."""
    return f"perm:{user_id}:{group_id}"


def ban_cache_key(user_id: str, group_id: str | None = None) -> str:
    """Return the cache key for global or group-scoped bans."""
    key = f"ban:{user_id}"
    if group_id:
        key += f":{group_id}"
    return key


def group_plugin_cache_key(group_id: str) -> str:
    """Return the cache key for group-level plugin disable state."""
    return f"group_plugin:{group_id}"


def group_bot_cache_key(group_id: str) -> str:
    """Return the cache key for group bot enablement state."""
    return f"group_bot:{group_id}"


def plugin_global_cache_key(plugin_module: str) -> str:
    """Return the cache key for global plugin enablement state."""
    return f"plugin_global:{plugin_module}"
