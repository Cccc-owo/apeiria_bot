"""Auth hook — pre-run permission, ban, and plugin status checks."""

from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor

from apeiria.domains.permissions import permission_service


@run_preprocessor
async def auth_hook(matcher: Matcher, event: Event, bot: Bot) -> None:
    """Global pre-run auth check."""
    plugin = matcher.plugin
    if not plugin:
        return

    await permission_service.assert_can_run_plugin(bot, event, plugin)
