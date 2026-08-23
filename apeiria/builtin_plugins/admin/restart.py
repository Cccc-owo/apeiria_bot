"""Implement the ``/restart`` command and restart notification on reconnect."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, cast

from arclet.alconna import CommandMeta
from nonebot import get_driver
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.log import logger
from nonebot_plugin_alconna import Alconna, on_alconna

from apeiria.utils.restart import graceful_restart

from .utils import ensure_owner_message

_CONTEXT_PATH = Path("data/.restart_context.json")
_MAX_RETRIES = 3
_RETRY_DELAY = 3.0

_restart = on_alconna(
    Alconna("restart", meta=CommandMeta(description="重启机器人")),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_restart.handle()
async def handle_restart(bot: Bot, event: Event) -> None:
    """Handle the ``/restart`` command, save context, and schedule the restart.

    Args:
        bot: The bot instance used to send responses.
        event: The message event that triggered the command.
    """
    owner_error = await ensure_owner_message(bot, event)
    if owner_error:
        await _restart.finish(owner_error)

    _save_context(bot, event)
    await _restart.send("已计划重启...")
    loop = asyncio.get_running_loop()
    loop.call_later(1.5, lambda: asyncio.ensure_future(_do_restart()))


def _save_context(bot: Bot, event: Event) -> None:
    """Save the current bot and session info as a restart recovery context.

    Args:
        bot: The current bot instance.
        event: The message event that triggered the command.
    """
    ctx: dict[str, Any] = {
        "bot_self_id": bot.self_id,
        "adapter_name": bot.adapter.get_name(),
        "message_type": getattr(event, "message_type", "private"),
        "user_id": _safe_attr(event, "get_user_id"),
        "group_id": getattr(event, "group_id", None),
        "session_id": _safe_attr(event, "get_session_id"),
        "started_at": time.time(),
    }
    _CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONTEXT_PATH.write_text(json.dumps(ctx))


def _safe_attr(event: Event, method: str) -> str | None:
    """Safely invoke a method on an event object and return its string result.

    Args:
        event: The event object to access.
        method: The name of the method to call.

    Returns:
        The string result of the method call, or None when unavailable.
    """
    try:
        return str(getattr(event, method)())
    except (AttributeError, TypeError):
        return None


def _read_context() -> dict[str, Any] | None:
    """Read and parse the restart recovery context.

    Returns:
        The parsed context dict, or None when missing or invalid.
    """
    if not _CONTEXT_PATH.exists():
        return None
    try:
        return json.loads(_CONTEXT_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        _CONTEXT_PATH.unlink(missing_ok=True)
        return None


def _delete_context() -> None:
    """Remove the restart recovery context file."""
    _CONTEXT_PATH.unlink(missing_ok=True)


class _RestartNotifyEvent:
    """A lightweight event used to notify the original session after restart."""

    def __init__(
        self,
        user_id: str | None,
        session_id: str,
        message_type: str,
        group_id: str | None,
    ) -> None:
        """Initialize the restart notification event.

        Args:
            user_id: The target user ID.
            session_id: The target session ID.
            message_type: The message type.
            group_id: The target group ID.
        """
        self._user_id = user_id
        self._session_id = session_id
        self.message_type = message_type
        self.group_id = group_id

    def get_type(self) -> str:
        """Return the event type identifier.

        Returns:
            The event type, always ``message``.
        """
        return "message"

    def get_user_id(self) -> str:
        """Return the target user ID.

        Returns:
            The target user ID, or an empty string when unset.
        """
        return self._user_id or ""

    def get_session_id(self) -> str:
        """Return the target session ID.

        Returns:
            The target session ID.
        """
        return self._session_id


@get_driver().on_bot_connect
async def _on_reconnect(bot: Bot) -> None:
    """Notify the original session when the bot reconnects after a restart.

    Args:
        bot: The reconnected bot instance.
    """
    ctx = _read_context()
    if not ctx:
        return
    if ctx.get("bot_self_id") != bot.self_id:
        return
    if ctx.get("adapter_name") != bot.adapter.get_name():
        return

    _delete_context()

    elapsed = time.time() - ctx.get("started_at", time.time())
    msg = f"重启完成，耗时 {elapsed:.1f}s"

    event = _RestartNotifyEvent(
        user_id=ctx.get("user_id"),
        session_id=ctx.get("session_id", f"{bot.self_id}_"),
        message_type=ctx.get("message_type", "private"),
        group_id=ctx.get("group_id"),
    )

    for attempt in range(_MAX_RETRIES):
        err = await _try_send(bot, event, msg)
        if err is None:
            return
        if attempt < _MAX_RETRIES - 1:
            await asyncio.sleep(_RETRY_DELAY)
    logger.warning("重启通知发送失败（已重试 {} 次）", _MAX_RETRIES)


async def _try_send(
    bot: Bot, event: _RestartNotifyEvent, message: str
) -> BaseException | None:
    """Attempt to send a message and return the first error encountered.

    Args:
        bot: The bot instance used to send the message.
        event: The event to associate with the send.
        message: The message text to send.

    Returns:
        The exception raised during the send, or None on success.
    """
    try:
        await bot.send(cast("Event", event), message)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        return exc
    return None


async def _do_restart() -> None:
    """Perform the actual graceful restart."""
    await graceful_restart()
