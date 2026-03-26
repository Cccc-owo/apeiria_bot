"""Auth hook — pre-run permission, ban, and plugin status checks."""

import contextlib

from nonebot.adapters import Bot, Event
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import get_plugin_extra
from apeiria.core.utils.permission import extract_group_id


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
    group_id = extract_group_id(session_id, user_id)

    from apeiria.core.utils.permission import is_plugin_globally_enabled

    if not await is_plugin_globally_enabled(plugin.module_name):
        logger.debug("Blocked globally disabled plugin {}", plugin.module_name)
        raise IgnoredException("plugin_globally_disabled")

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
    from apeiria.core.utils.permission import (
        is_banned,
        is_group_bot_enabled,
        is_plugin_enabled,
    )

    if not await is_group_bot_enabled(group_id):
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
