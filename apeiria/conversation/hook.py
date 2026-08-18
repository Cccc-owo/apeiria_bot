from __future__ import annotations

from nonebot.adapters import Event  # noqa: TC002
from nonebot.log import logger
from nonebot.params import Depends
from nonebot_plugin_uninfo import Session, get_session

from apeiria.conversation.store import append_message, ensure_session


async def _persist_inbound(
    event: Event,
    session: object | None,
) -> None:
    if event.get_type() != "message":
        return
    try:
        session_id = event.get_session_id()
        if session_id.startswith("webchat:"):
            return
        user_id = session.user.id if session is not None else event.get_user_id()
        text = event.get_plaintext()
        platform, scene_type, scene_id = _extract_session_meta(
            event, session_id, session
        )
        await ensure_session(session_id, platform, scene_type, scene_id)
        await append_message(
            session_id=session_id,
            role="user",
            content=text,
            user_id=user_id,
        )
    except Exception:  # noqa: BLE001
        logger.opt(exception=True).debug("Failed to persist inbound message")


def _extract_session_meta(
    event: Event,
    session_id: str,
    session: object | None,
) -> tuple[str, str, str]:
    if session is not None:
        return str(session.scope), session.scene.type.name.lower(), session.scene.id

    platform = _try_attr(event, "platform") or "unknown"
    scene_type = (
        _try_attr(event, "detail_type") or _try_attr(event, "message_type") or "unknown"
    ).lower()
    scene_id = _try_attr(event, "group_id") or _try_attr(event, "scene_id")
    if scene_id is None:
        scene_id = session_id.rsplit("_", 1)[-1] if "_" in session_id else session_id
    return platform, scene_type, scene_id


def _try_attr(obj: object, name: str) -> str | None:
    try:
        val = getattr(obj, name, None)
        return str(val) if val is not None else None
    except (AttributeError, TypeError):
        return None


async def persist(
    event: Event,
    session: Session | None = Depends(get_session),
) -> None:
    await _persist_inbound(event, session)


__all__ = ["persist"]
