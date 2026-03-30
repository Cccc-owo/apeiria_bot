"""Auth hook — pre-run permission, ban, and plugin status checks."""

from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor

from apeiria.core.guard import plugin_guard_service


@run_preprocessor
async def auth_hook(matcher: Matcher, event: Event, bot: Bot) -> None:
    """Global pre-run auth check."""
    plugin = matcher.plugin
    if not plugin:
        return

    await plugin_guard_service.assert_allowed(bot, event, plugin)
