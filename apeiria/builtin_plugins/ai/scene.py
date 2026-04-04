from nonebot.adapters import Bot, Event

from .config import AIPluginConfig
from .models import SceneContext


def build_scene_context(
    bot: Bot,
    event: Event,
    config: AIPluginConfig,
) -> SceneContext | None:
    try:
        speaker_id = event.get_user_id()
    except Exception:  # noqa: BLE001
        return None

    text = _extract_plain_text(event)
    session_id = _safe_get_session_id(event) or speaker_id
    message_type = _resolve_message_type(event)
    session_key = f"{bot.self_id}:{message_type}:{session_id}"
    speaker_name = _resolve_speaker_name(event, speaker_id)
    is_mentioned = _is_mentioned(event, bot)
    matched_trigger = _match_trigger(text, config.explicit_triggers)

    return SceneContext(
        chat_mode="group" if message_type == "group" else "private",
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        text=text,
        is_mentioned=is_mentioned,
        matched_trigger=matched_trigger,
        session_key=session_key,
    )


def _extract_plain_text(event: Event) -> str:
    message = getattr(event, "get_plaintext", None)
    if callable(message):
        try:
            return str(message()).strip()
        except Exception:  # noqa: BLE001
            return ""
    raw_message = getattr(event, "message", None)
    return str(raw_message).strip() if raw_message is not None else ""


def _safe_get_session_id(event: Event) -> str | None:
    try:
        return event.get_session_id()
    except Exception:  # noqa: BLE001
        return None


def _resolve_message_type(event: Event) -> str:
    message_type = getattr(event, "message_type", None)
    if isinstance(message_type, str) and message_type.strip():
        return message_type.strip()
    return "private"


def _resolve_speaker_name(event: Event, default: str) -> str:
    for attribute in ("sender", "user_name", "nickname"):
        value = getattr(event, attribute, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if attribute == "sender" and value is not None:
            nickname = getattr(value, "nickname", None)
            if isinstance(nickname, str) and nickname.strip():
                return nickname.strip()
            card = getattr(value, "card", None)
            if isinstance(card, str) and card.strip():
                return card.strip()
    return default


def _is_mentioned(event: Event, bot: Bot) -> bool:
    message = getattr(event, "message", None)
    if message is None:
        return False
    try:
        for segment in message:
            if getattr(segment, "type", None) != "at":
                continue
            target = segment.data.get("qq") or segment.data.get("target")
            if str(target) == str(bot.self_id):
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _match_trigger(text: str, triggers: list[str]) -> str | None:
    normalized = text.strip()
    if not normalized:
        return None
    lowered = normalized.lower()
    for trigger in triggers:
        candidate = trigger.strip()
        if not candidate:
            continue
        if lowered.startswith(candidate.lower()):
            return candidate
    return None
