"""Self-revoke plugin: let users revoke bot-sent messages.

Users reply to a message the bot sent and send either "撤回" or "revoke" to
trigger a revoke of that message. This module wires up the matchers, the
permission check, and the revoke flow.
"""

from __future__ import annotations

from contextlib import suppress

from nonebot import get_driver
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.log import logger
from nonebot.matcher import Matcher  # noqa: TC002
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.plugin.on import on_fullmatch, on_message
from nonebot.rule import Rule

from .config import SelfRevokeConfig, get_self_revoke_config
from .providers import _resolve_provider

__plugin_meta__ = PluginMetadata(
    name="撤回消息",
    description="用户引用回复机器人消息来触发撤回。",
    homepage="https://github.com/Cccc-owo/apeiria_bot",
    usage="回复机器人的消息并发送「撤回」或「revoke」。",
    type="application",
    config=SelfRevokeConfig,
    supported_adapters={
        "~onebot.v11",
        "~onebot.v12",
        "~telegram",
        "~discord",
        "~feishu",
        "~satori",
        "~qq",
        "~milky",
    },
)


async def _is_superuser_event(bot: Bot, event: Event) -> bool:
    """Return whether the event was sent by a superuser.

    Any exception raised while evaluating the permission is suppressed and
    treated as a non-superuser sender.

    Args:
        bot: The bot instance handling the event.
        event: The incoming event to check.

    Returns:
        True if the event sender is a superuser, False otherwise.
    """
    with suppress(Exception):
        return await SUPERUSER(bot, event)
    return False


def _strip_command_prefix(text: str) -> str | None:
    """Strip the configured command prefix from a message text.

    Args:
        text: The raw message text.

    Returns:
        The text with the matching command prefix removed, or None if no
        configured prefix matches.
    """
    try:
        command_start = getattr(get_driver().config, "command_start", {"/"})
    except Exception:  # noqa: BLE001
        command_start = {"/"}
    if isinstance(command_start, str):
        command_start = {command_start}
    if not isinstance(command_start, (set, list, tuple)):
        command_start = {"/"}
    prefixes = sorted(
        (str(item) for item in command_start if str(item)),
        key=len,
        reverse=True,
    )
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return None


async def _is_prefixed_revoke(event: Event) -> bool:
    """Return whether the event text is a command-prefixed revoke request.

    Any exception raised while reading the event text is suppressed and treated
    as an absence of a prefixed revoke request.

    Args:
        event: The incoming message event.

    Returns:
        True if the text uses a command prefix followed by a revoke keyword,
        False otherwise.
    """
    with suppress(Exception):
        text = event.get_plaintext().strip()
        prefix = _strip_command_prefix(text)
        if prefix is None:
            return False
        return prefix.lower() in {"撤回", "revoke"}
    return False


_prefixless_revoke = on_fullmatch(
    ("撤回", "revoke"),
    ignorecase=True,
    priority=8,
    block=False,
)
_prefixed_revoke = on_message(
    Rule(_is_prefixed_revoke),
    priority=8,
    block=False,
)


@_prefixless_revoke.handle()
@_prefixed_revoke.handle()
async def handle_revoke(  # noqa: C901
    bot: Bot,
    event: Event,
    matcher: Matcher,  # noqa: ARG001
) -> None:
    """Handle a revoke request for a message the bot sent.

    Resolve the message the user replied to, verify the bot authored it and
    the caller is allowed to revoke, then revoke the target message and
    optionally the trigger message.

    Args:
        bot: The bot instance handling the event.
        event: The incoming message event.
        matcher: The matcher that triggered this handler.
    """
    config = get_self_revoke_config()
    provider = _resolve_provider(bot, event)
    if provider is None:
        return

    target = await provider.get_reply_target(bot, event)
    if target is None:
        return

    if config.permission == "superuser" and not await _is_superuser_event(bot, event):
        if config.feedback == "reaction":
            with suppress(Exception):
                await provider.apply_feedback(bot, event, kind="failure")
        return

    if not await provider.is_bot_authored(bot, event, target):
        if config.feedback == "reaction":
            with suppress(Exception):
                await provider.apply_feedback(bot, event, kind="failure")
        return

    revoke_result = await provider.revoke_message(bot, event, target)
    if not revoke_result.success:
        logger.warning("撤回目标消息失败: {}", revoke_result.reason)
        if config.feedback == "reaction":
            with suppress(Exception):
                await provider.apply_feedback(bot, event, kind="failure")
        return

    if config.revoke_trigger_message:
        with suppress(Exception):
            await provider.revoke_trigger_message(bot, event)

    if not config.revoke_trigger_message and config.feedback == "reaction":
        with suppress(Exception):
            await provider.apply_feedback(bot, event, kind="success")


__all__ = ["_prefixed_revoke", "_prefixless_revoke", "handle_revoke"]
