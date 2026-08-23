"""Persistence layer for conversation sessions and messages."""

from __future__ import annotations

from typing import cast

from sqlalchemy import CursorResult, delete, select

from apeiria.db.base import _now_iso
from apeiria.db.engine import get_db
from apeiria.db.models.conversation import Message, Session


async def ensure_session(
    session_id: str,
    platform: str,
    scene_type: str,
    scene_id: str,
) -> Session:
    """Ensure a session row exists and return it from the database.

    When a session with ``session_id`` already exists its ``updated_at``
    timestamp is refreshed; otherwise a new session is created, added, and
    flushed.

    Args:
        session_id: The unique session identifier.
        platform: The platform name, e.g. ``onebot``.
        scene_type: The scene type, e.g. ``group`` or ``private``.
        scene_id: The identifier of the scene within the platform.

    Returns:
        The existing or newly created session.
    """
    db = get_db()
    now = _now_iso()
    async with db.gate.write() as sess:
        existing = (
            await sess.execute(select(Session).where(Session.session_id == session_id))
        ).scalar_one_or_none()
        if existing:
            existing.updated_at = now
            return existing
        new_session = Session(
            session_id=session_id,
            platform=platform,
            scene_type=scene_type,
            scene_id=scene_id,
        )
        sess.add(new_session)
        await sess.flush()
        return new_session


async def append_message(  # noqa: PLR0913
    session_id: str,
    role: str,
    content: str,
    *,
    user_id: str | None = None,
    message_id: str | None = None,
    meta_json: dict | None = None,
) -> Message | None:
    """Append a message to the given session.

    When the session does not exist, a warning is logged and ``None`` is
    returned without creating a message.

    Args:
        session_id: The unique session identifier to append to.
        role: The message role, e.g. ``user`` or ``assistant``.
        content: The message text content.
        user_id: Optional identifier of the message author.
        message_id: Optional message identifier from the platform.
        meta_json: Optional arbitrary metadata JSON stored with the message.

    Returns:
        The newly created message, or ``None`` when the session is missing.
    """
    db = get_db()
    now = _now_iso()
    async with db.gate.write() as sess:
        session = (
            await sess.execute(select(Session).where(Session.session_id == session_id))
        ).scalar_one_or_none()
        if session is None:
            from nonebot.log import logger

            logger.warning(
                "append_message: session not found, skipping: {}", session_id
            )
            return None

        msg = Message(
            session_id=session.id,
            role=role,
            content=content,
            user_id=user_id,
            message_id=message_id,
            time=now,
            meta_json=meta_json,
        )
        sess.add(msg)
        session.updated_at = now
        await sess.flush()
        return msg


async def load_recent(
    session_id: str,
    limit: int = 20,
) -> list[Message]:
    """Return the most recent messages of a session, newest first.

    Args:
        session_id: The unique session identifier.
        limit: Maximum number of messages to return, defaults to 20.

    Returns:
        The most recent messages ordered by id descending, or an empty list
        when the session is missing.
    """
    db = get_db()
    async with db.gate.read() as sess:
        session = (
            await sess.execute(select(Session).where(Session.session_id == session_id))
        ).scalar_one_or_none()
        if session is None:
            return []
        result = await sess.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def search_messages(
    session_id: str,
    keyword: str,
    limit: int = 10,
) -> list[Message]:
    """Return messages of a session that contain a keyword, newest first.

    Args:
        session_id: The unique session identifier.
        keyword: Text to search for within the message content.
        limit: Maximum number of messages to return, defaults to 10.

    Returns:
        Matching messages ordered by id descending, or an empty list when the
        session is missing.
    """
    db = get_db()
    async with db.gate.read() as sess:
        session = (
            await sess.execute(select(Session).where(Session.session_id == session_id))
        ).scalar_one_or_none()
        if session is None:
            return []
        result = await sess.execute(
            select(Message)
            .where(
                Message.session_id == session.id,
                Message.content.contains(keyword),
            )
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def delete_session_messages(session_id: str) -> int:
    """Delete all messages of a session while keeping the session row.

    Args:
        session_id: The unique session identifier.

    Returns:
        The number of messages deleted.
    """
    db = get_db()
    async with db.gate.write() as sess:
        session = (
            await sess.execute(select(Session).where(Session.session_id == session_id))
        ).scalar_one_or_none()
        if session is None:
            return 0
        result = await sess.execute(
            delete(Message).where(Message.session_id == session.id)
        )
        return cast("CursorResult", result).rowcount or 0


async def delete_message(message_id: str) -> int:
    """Delete a single message by its message identifier.

    Args:
        message_id: The message identifier to delete.

    Returns:
        The number of messages deleted, either 0 or 1.
    """
    db = get_db()
    async with db.gate.write() as sess:
        result = await sess.execute(
            delete(Message).where(Message.message_id == message_id)
        )
        return cast("CursorResult", result).rowcount or 0
