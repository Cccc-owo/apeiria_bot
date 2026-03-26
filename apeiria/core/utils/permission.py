"""Permission checking utilities."""

from __future__ import annotations

from apeiria.domains.permissions import permission_service


def extract_group_id(session_id: str, user_id: str) -> str | None:
    """Extract group_id from a NoneBot session id."""
    return permission_service.extract_group_id(session_id, user_id)


async def invalidate_user_level_cache(user_id: str, group_id: str) -> None:
    await permission_service.invalidate_user_level_cache(user_id, group_id)


async def invalidate_ban_cache(user_id: str, group_id: str | None = None) -> None:
    await permission_service.invalidate_ban_cache(user_id, group_id)


async def invalidate_group_plugin_cache(group_id: str) -> None:
    await permission_service.invalidate_group_plugin_cache(group_id)


async def invalidate_group_bot_status_cache(group_id: str) -> None:
    await permission_service.invalidate_group_bot_status_cache(group_id)


async def get_user_level(user_id: str, group_id: str) -> int:
    """Get user's permission level in a group.

    Checks cache first, falls back to DB query.
    """
    return await permission_service.get_user_level(user_id, group_id)


async def check_permission(user_id: str, group_id: str, required_level: int) -> bool:
    """Check if user meets the required permission level."""
    return await permission_service.check_permission(user_id, group_id, required_level)


async def is_banned(user_id: str, group_id: str | None = None) -> bool:
    """Check if a user is banned (globally or in a specific group)."""
    return await permission_service.is_banned(user_id, group_id)


async def is_plugin_enabled(group_id: str, plugin_module: str) -> bool:
    """Check if a plugin is enabled in a group."""
    return await permission_service.is_plugin_enabled(group_id, plugin_module)


async def is_group_bot_enabled(group_id: str) -> bool:
    """Check whether the bot is enabled for a group."""
    return await permission_service.is_group_bot_enabled(group_id)


async def is_plugin_globally_enabled(plugin_module: str) -> bool:
    """Check if a plugin is globally enabled."""
    return await permission_service.is_plugin_globally_enabled(plugin_module)


async def set_user_level(user_id: str, group_id: str, level: int) -> None:
    """Set user's permission level in a group. Invalidates cache."""
    await permission_service.set_user_level(user_id, group_id, level)
