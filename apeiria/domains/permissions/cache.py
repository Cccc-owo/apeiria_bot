"""Cache adapter for permission-related state."""

from __future__ import annotations

from apeiria.core.services.cache import get_cache
from apeiria.domains.permissions.cache_keys import (
    ban_cache_key,
    group_bot_cache_key,
    group_plugin_cache_key,
    plugin_global_cache_key,
    user_level_cache_key,
)


class PermissionCache:
    """Own cache reads, writes, and invalidation for permission state."""

    async def get_user_level(self, user_id: str, group_id: str) -> int | None:
        cached = await get_cache().get(user_level_cache_key(user_id, group_id))
        if cached is None:
            return None
        return int(cached)

    async def set_user_level(self, user_id: str, group_id: str, level: int) -> None:
        await get_cache().set(user_level_cache_key(user_id, group_id), level, ttl=300)

    async def invalidate_user_level(self, user_id: str, group_id: str) -> None:
        await get_cache().delete(user_level_cache_key(user_id, group_id))

    async def get_ban(self, user_id: str, group_id: str | None = None) -> bool | None:
        cached = await get_cache().get(ban_cache_key(user_id, group_id))
        if cached is None:
            return None
        return bool(cached)

    async def set_ban(
        self,
        user_id: str,
        group_id: str | None,
        *,
        banned: bool,
    ) -> None:
        await get_cache().set(ban_cache_key(user_id, group_id), banned, ttl=60)

    async def invalidate_ban(self, user_id: str, group_id: str | None = None) -> None:
        cache = get_cache()
        await cache.delete(ban_cache_key(user_id))
        if group_id:
            await cache.delete(ban_cache_key(user_id, group_id))

    async def get_group_disabled_plugins(self, group_id: str) -> list[str] | None:
        cached = await get_cache().get(group_plugin_cache_key(group_id))
        if cached is None:
            return None
        return list(cached)

    async def set_group_disabled_plugins(
        self,
        group_id: str,
        disabled_plugins: list[str],
    ) -> None:
        await get_cache().set(
            group_plugin_cache_key(group_id),
            disabled_plugins,
            ttl=120,
        )

    async def invalidate_group_disabled_plugins(self, group_id: str) -> None:
        await get_cache().delete(group_plugin_cache_key(group_id))

    async def get_group_bot_enabled(self, group_id: str) -> bool | None:
        cached = await get_cache().get(group_bot_cache_key(group_id))
        if cached is None:
            return None
        return bool(cached)

    async def set_group_bot_enabled(self, group_id: str, *, enabled: bool) -> None:
        await get_cache().set(group_bot_cache_key(group_id), enabled, ttl=120)

    async def invalidate_group_bot_enabled(self, group_id: str) -> None:
        await get_cache().delete(group_bot_cache_key(group_id))

    async def get_plugin_global_enabled(self, plugin_module: str) -> bool | None:
        cached = await get_cache().get(plugin_global_cache_key(plugin_module))
        if cached is None:
            return None
        return bool(cached)

    async def set_plugin_global_enabled(
        self,
        plugin_module: str,
        *,
        enabled: bool,
    ) -> None:
        await get_cache().set(plugin_global_cache_key(plugin_module), enabled, ttl=120)

    async def invalidate_plugin_global_enabled(self, plugin_module: str) -> None:
        await get_cache().delete(plugin_global_cache_key(plugin_module))


permission_cache = PermissionCache()
