"""Auth hook — pre-run permission, ban, and plugin status checks."""

import contextlib

from nonebot.adapters import Bot, Event
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import get_plugin_extra


@run_preprocessor
async def auth_hook(matcher: Matcher, event: Event, bot: Bot) -> None:
    """Global pre-run auth check."""
    plugin = matcher.plugin
    if not plugin:
        return

    try:
        user_id = event.get_user_id()
    except Exception:  # noqa: BLE001
        return

    session_id = event.get_session_id()
    group_id = _extract_group_id(session_id, user_id)

    from nonebot import get_driver

    if user_id in get_driver().config.superusers:
        return

    if group_id:
        await _check_group_auth(bot, event, user_id, group_id, plugin.module_name)
    else:
        await _check_private_auth(bot, event, user_id)

    await _check_plugin_level(bot, event, plugin, user_id, group_id)


async def _check_group_auth(
    bot: Bot, event: Event, user_id: str, group_id: str, module_name: str
) -> None:
    """Check bot status, ban, and plugin enabled in group context."""
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole
    from apeiria.core.utils.permission import is_banned, is_plugin_enabled

    async with get_session() as session:
        result = await session.execute(
            select(GroupConsole.bot_status).where(GroupConsole.group_id == group_id)
        )
        bot_status = result.scalar_one_or_none()
        if bot_status is False:
            raise IgnoredException("bot_disabled")

    if await is_banned(user_id, group_id):
        logger.debug("Blocked banned user {} in group {}", user_id, group_id)
        with contextlib.suppress(Exception):
            await bot.send(event, t("auth.banned"))
        raise IgnoredException("user_banned")

    if not await is_plugin_enabled(group_id, module_name):
        with contextlib.suppress(Exception):
            await bot.send(event, t("auth.plugin_disabled"))
        raise IgnoredException("plugin_disabled")


async def _check_private_auth(bot: Bot, event: Event, user_id: str) -> None:
    """Check ban in private context."""
    from apeiria.core.utils.permission import is_banned

    if await is_banned(user_id):
        logger.debug("Blocked banned user {} in private", user_id)
        with contextlib.suppress(Exception):
            await bot.send(event, t("auth.banned"))
        raise IgnoredException("user_banned")


async def _check_plugin_level(
    bot: Bot,
    event: Event,
    plugin: object,
    user_id: str,
    group_id: str | None,
) -> None:
    """Check if user meets plugin's required permission level."""
    extra = get_plugin_extra(plugin)  # type: ignore[arg-type]
    required_level = extra.admin_level if extra else 0

    if required_level <= 0 or not group_id:
        return

    from apeiria.core.utils.permission import get_user_level
    from apeiria.core.utils.rules import _get_adapter_role_level

    adapter_level = await _get_adapter_role_level(bot, event, group_id)
    if adapter_level >= required_level:
        return

    db_level = await get_user_level(user_id, group_id)
    effective = max(adapter_level, db_level)
    if effective < required_level:
        logger.debug(
            "Permission denied: {} needs level {} but has {}",
            user_id,
            required_level,
            effective,
        )
        _level_names = {5: t("auth.level_admin"), 6: t("auth.level_owner")}
        need = _level_names.get(required_level, f"Lv.{required_level}")
        with contextlib.suppress(Exception):
            await bot.send(event, t("auth.permission_denied", need=need))
        raise IgnoredException("insufficient_permission")


def _extract_group_id(session_id: str, user_id: str) -> str | None:
    """Extract group_id from session_id."""
    if session_id == user_id:
        return None
    if "_" in session_id:
        parts = session_id.split("_")
        if len(parts) >= 2:  # noqa: PLR2004
            return parts[1] if parts[0] == "group" else parts[0]
    return None
