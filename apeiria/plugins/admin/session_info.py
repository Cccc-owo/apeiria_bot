"""Session identity inspection command."""

from __future__ import annotations

from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot_plugin_alconna import Alconna, on_alconna

_session = on_alconna(
    Alconna("sid"),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_session.handle()
async def handle_session(bot: Bot, event: Event) -> None:
    session_id = _safe_get_session_id(event) or ""
    user_id = _safe_get_user_id(event) or ""
    message_type = _resolve_message_type(event)
    source_id = f"{bot.self_id}:{message_type}:{session_id}"
    lines = [
        f"SID: 「{source_id}」",
        f"UID: 「{user_id}」",
        "消息会话来源信息:",
        f"  机器人 ID: 「{bot.self_id}」",
        f"  消息类型: 「{message_type}」",
        f"  会话 ID: 「{session_id}」",
    ]
    await _session.finish("\n".join(lines))


def _safe_get_user_id(event: Event) -> str | None:
    try:
        return event.get_user_id()
    except Exception:  # noqa: BLE001
        return None


def _safe_get_session_id(event: Event) -> str | None:
    try:
        return event.get_session_id()
    except Exception:  # noqa: BLE001
        return None


def _resolve_message_type(event: Event) -> str:
    message_type = getattr(event, "message_type", None)
    if isinstance(message_type, str) and message_type.strip():
        return message_type.strip()
    return event.__class__.__name__
