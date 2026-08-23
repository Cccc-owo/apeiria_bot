"""Implement the ``/sid`` command for showing current session information."""

from __future__ import annotations

from arclet.alconna import CommandMeta
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot_plugin_alconna import Alconna, on_alconna

from .presenter import render_block
from .utils import ensure_owner_message

_session = on_alconna(
    Alconna("sid", meta=CommandMeta(description="查看会话信息")),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_session.handle()
async def handle_session(bot: Bot, event: Event) -> None:
    """Handle the ``/sid`` command and show the current session information.

    Args:
        bot: The bot instance used to send responses.
        event: The message event that triggered the command.
    """
    owner_error = await ensure_owner_message(bot, event)
    if owner_error:
        await _session.finish(owner_error)

    session_id = _safe_get_session_id(event) or "?"
    user_id = _safe_get_user_id(event) or "?"
    message_type = _resolve_message_type(event)
    source_id = f"{bot.self_id}:{message_type}:{session_id}"
    await _session.finish(
        render_block(
            "会话信息",
            [
                ("Bot", bot.self_id),
                ("用户", user_id),
                ("会话", session_id),
                ("类型", message_type),
                ("SID", source_id),
            ],
        )
    )


def _safe_get_user_id(event: Event) -> str | None:
    """Return the user id for an event, or ``None`` if it cannot be resolved.

    Args:
        event: The chat event to inspect.

    Returns:
        The user id, or ``None`` when the adapter cannot provide one.
    """
    try:
        return event.get_user_id()
    except Exception:  # noqa: BLE001
        return None


def _safe_get_session_id(event: Event) -> str | None:
    """Return the session id for an event, or ``None`` if it cannot be resolved.

    Args:
        event: The chat event to inspect.

    Returns:
        The session id, or ``None`` when the adapter cannot provide one.
    """
    try:
        return event.get_session_id()
    except Exception:  # noqa: BLE001
        return None


def _resolve_message_type(event: Event) -> str:
    """Resolve a human-readable message type for an event.

    Args:
        event: The chat event to inspect.

    Returns:
        The message type, or the event class name as a fallback.
    """
    message_type = getattr(event, "message_type", None)
    if isinstance(message_type, str) and message_type.strip():
        return message_type.strip()
    return event.__class__.__name__
