"""Permission checking utilities."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from nonebot.log import logger

from apeiria.core.services.cache import get_cache


async def get_user_level(user_id: str, group_id: str) -> int:
    """Get user's permission level in a group.

    Checks cache first, falls back to DB query.
    """
    cache = get_cache()
    cache_key = f"perm:{user_id}:{group_id}"

    cached = await cache.get(cache_key)
    if cached is not None:
        return int(cached)

    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.level import LevelUser

    async with get_session() as session:
        result = await session.execute(
            select(LevelUser.level).where(
                LevelUser.user_id == user_id, LevelUser.group_id == group_id
            )
        )
        row = result.scalar_one_or_none()
        level = row if row is not None else 0

    await cache.set(cache_key, level, ttl=300)
    return level


async def check_permission(user_id: str, group_id: str, required_level: int) -> bool:
    """Check if user meets the required permission level."""
    level = await get_user_level(user_id, group_id)
    return level >= required_level


async def is_banned(user_id: str, group_id: str | None = None) -> bool:
    """Check if a user is banned (globally or in a specific group)."""
    cache = get_cache()
    cache_key = f"ban:{user_id}"
    if group_id:
        cache_key += f":{group_id}"

    cached = await cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.ban import BanConsole

    async with get_session() as session:
        stmt = select(BanConsole).where(BanConsole.user_id == user_id)
        if group_id:
            stmt = stmt.where(
                (BanConsole.group_id == group_id) | (BanConsole.group_id.is_(None))
            )
        result = await session.execute(stmt)
        bans = result.scalars().all()

    now = datetime.now(timezone.utc)
    banned = False
    for ban in bans:
        if ban.duration == 0:
            banned = True
            break
        if ban.ban_time and ban.duration > 0:
            bt = ban.ban_time
            if bt.tzinfo is None:
                bt = bt.replace(tzinfo=timezone.utc)
            elapsed = (now - bt).total_seconds()
            if elapsed < ban.duration:
                banned = True
                break

    await cache.set(cache_key, banned, ttl=60)
    return banned


async def is_plugin_enabled(group_id: str, plugin_module: str) -> bool:
    """Check if a plugin is enabled in a group."""
    from apeiria.core.utils.helpers import is_plugin_protected

    if is_plugin_protected(plugin_module):
        return True

    cache = get_cache()
    cache_key = f"group_plugin:{group_id}"

    cached = await cache.get(cache_key)
    if cached is not None:
        disabled: list[str] = cached
    else:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.group import GroupConsole

        async with get_session() as session:
            result = await session.execute(
                select(GroupConsole.disabled_plugins).where(
                    GroupConsole.group_id == group_id
                )
            )
            raw = result.scalar_one_or_none()
            try:
                disabled = json.loads(raw) if raw else []
            except (json.JSONDecodeError, TypeError):
                disabled = []
        await cache.set(cache_key, disabled, ttl=120)

    return plugin_module not in disabled


async def is_plugin_globally_enabled(plugin_module: str) -> bool:
    """Check if a plugin is globally enabled."""
    from apeiria.core.utils.helpers import is_plugin_protected

    if is_plugin_protected(plugin_module):
        return True

    cache = get_cache()
    cache_key = f"plugin_global:{plugin_module}"

    cached = await cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.plugin_info import PluginInfo

    async with get_session() as session:
        result = await session.execute(
            select(PluginInfo.is_global_enabled).where(
                PluginInfo.module_name == plugin_module
            )
        )
        enabled = result.scalar_one_or_none()

    value = True if enabled is None else bool(enabled)
    await cache.set(cache_key, value, ttl=120)
    return value


async def set_user_level(user_id: str, group_id: str, level: int) -> None:
    """Set user's permission level in a group. Invalidates cache."""
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.level import LevelUser

    async with get_session() as session:
        result = await session.execute(
            select(LevelUser).where(
                LevelUser.user_id == user_id, LevelUser.group_id == group_id
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.level = level
        else:
            session.add(LevelUser(user_id=user_id, group_id=group_id, level=level))
        await session.commit()

    cache = get_cache()
    await cache.delete(f"perm:{user_id}:{group_id}")
    logger.debug("Set level {}:{} -> {}", user_id, group_id, level)
