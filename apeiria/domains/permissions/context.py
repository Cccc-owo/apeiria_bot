"""Pure helpers for permission context and adapter role extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from nonebot.adapters import Bot, Event


ConversationType = Literal["private", "group", "other"]


def extract_group_id(session_id: str, user_id: str) -> str | None:
    """Extract a group identifier from a session id when adapter data is absent."""
    if session_id == user_id:
        return None
    if "_" in session_id:
        parts = session_id.split("_")
        if len(parts) >= 2:  # noqa: PLR2004
            return parts[1] if parts[0] == "group" else parts[0]
    return None


def group_id_from_event(event: Event) -> str | None:
    """Resolve a group id from common event shapes."""
    group_id = getattr(event, "group_id", None)
    if group_id is not None:
        return str(group_id)

    try:
        user_id = event.get_user_id()
        return extract_group_id(event.get_session_id(), user_id)
    except Exception:  # noqa: BLE001
        return None


def resolve_conversation_type(
    event: Event,
    user_id: str,
    group_id: str | None,
) -> ConversationType:
    """Normalize the conversation type used by permission checks."""
    if group_id is not None:
        return "group"
    if is_private_event(event, user_id):
        return "private"
    return "other"


def is_private_event(event: Event, user_id: str) -> bool:
    """Return whether the event is a private conversation."""
    detail_type = getattr(event, "detail_type", None)
    if detail_type == "private":
        return True
    try:
        return event.get_session_id() == user_id
    except Exception:  # noqa: BLE001
        return False


def get_event_role_level(event: Event) -> int:
    """Read adapter role level directly from event payload when available."""
    sender = getattr(event, "sender", None)
    sender_role = getattr(sender, "role", None)
    if isinstance(sender_role, str):
        return map_role_to_level(sender_role)

    role = getattr(event, "role", None)
    if isinstance(role, str):
        return map_role_to_level(role)
    return 0


def is_onebot_api_available(bot: Bot) -> bool:
    """Return whether the bot exposes OneBot-style member role APIs."""
    adapter = getattr(bot, "adapter", None)
    get_name = getattr(adapter, "get_name", None)
    if not callable(get_name):
        return False
    adapter_name = str(get_name()).lower()
    return "onebot" in adapter_name


def to_onebot_numeric_id(value: str) -> int | None:
    """Convert a textual id into a OneBot-compatible numeric id."""
    normalized = value.strip()
    if not normalized.isdigit():
        return None
    return int(normalized)


def map_role_to_level(role: object) -> int:
    """Map adapter role names onto Apeiria permission levels."""
    if not isinstance(role, str):
        return 0
    if role == "owner":
        return 6
    if role == "admin":
        return 5
    return 0
