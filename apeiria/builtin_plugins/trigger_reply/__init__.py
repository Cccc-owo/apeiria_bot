"""Trigger-reply plugin: respond to specific messages via standalone rule files."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from nonebot import require
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.log import logger
from nonebot.matcher import Matcher  # noqa: TC002
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.plugin.on import on_message
from nonebot.rule import Rule
from nonebot.typing import T_State  # noqa: TC002

require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")
from nonebot_plugin_uninfo import Uninfo  # noqa: TC002

from .config import TriggerReplyConfig, get_trigger_reply_config
from .loader import collect_rule_files
from .models import MatchResult, TriggerInput
from .service import TriggerRuleSet

__plugin_meta__ = PluginMetadata(
    name="触发回复",
    description="按独立规则文件响应特定消息。",
    homepage="https://github.com/Cccc-owo/apeiria_bot",
    usage="在规则文件中配置 rule、match 与 reply 后自动回复。",
    type="application",
    config=TriggerReplyConfig,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

_rule_set: TriggerRuleSet | None = None
_rule_paths: tuple[Path, ...] = ()


def _extract_input(
    bot: Bot,
    event: Event,
    session: Uninfo | None,
) -> TriggerInput | None:
    """Build a trigger input from a message event and session context.

    Args:
        bot: The adapter bot instance handling the event.
        event: The incoming event.
        session: Session info, or ``None`` when unavailable.

    Returns:
        A :class:`TriggerInput` for message events, or ``None`` when the event
        is not a message.
    """
    with suppress(Exception):
        if event.get_type() != "message":
            return None

    if session is None:
        user_id = None
        group_id = None
        platform = None
        with suppress(Exception):
            user_id = str(event.get_user_id())
        user_name = None
        group_name = None
    else:
        user_id = session.user.id
        group_id = session.scene.id if session.scene.is_group else None
        platform = str(session.scope)
        with suppress(Exception):
            user_name = session.user.nick or session.user.name or None
        with suppress(Exception):
            group_name = session.scene.name if session.scene.is_group else None

    bot_id = None
    with suppress(Exception):
        bot_id = bot.self_id
    message_text = ""
    with suppress(Exception):
        message_text = str(event.get_message())
    plaintext = ""
    with suppress(Exception):
        plaintext = str(event.get_plaintext())
    is_to_me = False
    with suppress(Exception):
        is_to_me = event.is_tome()
    message_id = None
    with suppress(Exception):
        raw_message_id = getattr(event, "message_id", None)
        if raw_message_id is not None:
            message_id = str(raw_message_id)

    ts = getattr(event, "time", None)
    now = datetime.now(UTC).astimezone()
    tz = now.tzinfo
    dt = datetime.fromtimestamp(ts, tz=tz) if isinstance(ts, (int, float)) else now

    return TriggerInput(
        platform=platform,
        bot_id=str(bot_id) if bot_id else None,
        user_id=user_id,
        group_id=group_id,
        message_text=message_text,
        plaintext=plaintext,
        is_to_me=is_to_me,
        user_name=user_name,
        group_name=group_name,
        message_id=message_id,
        time=dt.strftime("%H:%M"),
        date=dt.strftime("%Y-%m-%d"),
    )


def _get_rule_set(config: TriggerReplyConfig) -> TriggerRuleSet | None:
    """Load or reload the trigger rule set as needed.

    Rebuilds the rule set when no set is cached yet or when the rule files
    change; on reload errors the previously cached rules are kept.

    Args:
        config: The trigger-reply configuration.

    Returns:
        The current rule set.
    """
    global _rule_set, _rule_paths  # noqa: PLW0603

    paths = tuple(collect_rule_files(config))
    if _rule_set is None or paths != _rule_paths:
        new_set, errors = TriggerRuleSet.load(paths)
        if errors:
            logger.warning("触发回复初始加载存在错误: {}", "; ".join(errors))
        _rule_set = new_set
        _rule_paths = paths
        return _rule_set

    if _rule_set.has_changed():
        new_set, errors = TriggerRuleSet.load(paths)
        if errors:
            logger.warning(
                "触发回复重载失败，保留旧规则: {}",
                "; ".join(errors),
            )
        else:
            _rule_set = new_set
    return _rule_set


async def _rule_checker(
    bot: Bot,
    event: Event,
    state: T_State,
    session: Uninfo,
) -> bool:
    """Check whether an event matches any trigger rule.

    Args:
        bot: The adapter bot instance handling the event.
        event: The incoming event.
        state: The message-processing state.
        session: Session info for the message.

    Returns:
        ``True`` when a rule matches and the result is stored in ``state``,
        otherwise ``False``.
    """
    config = get_trigger_reply_config()
    if not config.enabled:
        return False
    trigger = _extract_input(bot, event, session)
    if trigger is None:
        if config.debug:
            logger.debug("触发回复跳过: 不支持的消息输入")
        return False
    rule_set = _get_rule_set(config)
    if rule_set is None:
        return False
    result = rule_set.match(trigger)
    if result is None:
        if config.debug:
            logger.debug("触发回复跳过: 无匹配规则")
        return False
    state["_trigger_reply_result"] = result
    return True


_message = on_message(
    Rule(_rule_checker),
    priority=12,
    block=False,
)


@_message.handle()
async def handle_trigger_message(matcher: Matcher, state: T_State) -> None:
    """Send the matched trigger reply for a message.

    Args:
        matcher: The active matcher for the message.
        state: The message-processing state containing the match result.
    """
    result: MatchResult | None = state.get("_trigger_reply_result")
    if result is None:
        return
    if result.rule.block:
        matcher.stop_propagation()
    await matcher.send(result.text)


__all__ = ["_message", "handle_trigger_message"]
