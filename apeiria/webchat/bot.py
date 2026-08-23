"""WebChat bot instance that serializes outbound messages back to the browser."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment
from nonebot.log import logger

from apeiria.db.base import _now_iso
from apeiria.webchat import protocol
from apeiria.webchat.event import WebChatMessageEvent
from apeiria.webchat.message import Message, MessageSegment

if TYPE_CHECKING:
    from nonebot.adapters import Adapter, Event

    from apeiria.webchat.connection import ConnectionManager


class WebChatBot(BaseBot):
    """WebChat bot that serializes outbound messages back to the browser."""

    def __init__(
        self,
        adapter: Adapter,
        self_id: str,
        connections: ConnectionManager,
    ) -> None:
        """Initialize the bot with its adapter, self id, and connection manager.

        Args:
            adapter: The adapter that owns this bot.
            self_id: The bot's self identifier.
            connections: The connection manager used to route outbound frames.
        """
        super().__init__(adapter, self_id)
        self.connections = connections

    async def send(
        self,
        event: Event,
        message: str | BaseMessage | BaseMessageSegment,
        **kwargs: Any,  # noqa: ARG002
    ) -> Any:
        """Serialize a message to wire format, send it to the browser, and persist it.

        Args:
            event: The event that triggered the outbound send.
            message: The message to send, as text, a message, or a single segment.
            **kwargs: Extra send options (unused).

        Returns:
            A dict containing the generated ``message_id``.
        """
        if isinstance(message, Message):
            msg = message
        elif isinstance(message, MessageSegment):
            msg = Message([message])
        else:
            msg = Message(str(message))
        segments = protocol.message_to_wire(msg)
        message_id = uuid4().hex
        session_id = event.get_session_id()
        connection_id = (
            event.connection_id if isinstance(event, WebChatMessageEvent) else ""
        )

        wire = protocol.wire_message(
            message_id=message_id,
            role="bot",
            segments=segments,
            time=_now_iso(),
            session_id=session_id,
            user_id=self.self_id,
        )
        frame = protocol.message_frame(wire)
        if connection_id:
            await self.connections.send_to(connection_id, frame)
        else:
            await self.connections.broadcast(frame)

        await self._persist_outbound(event, session_id, message_id, msg, segments)
        return {"message_id": message_id}

    async def _persist_outbound(
        self,
        event: Event,
        session_id: str,
        message_id: str,
        msg: Message,
        segments: list[dict[str, Any]],
    ) -> None:
        """Persist an outbound bot message to the conversation store.

        Args:
            event: The event that triggered the outbound send.
            session_id: The session the message belongs to.
            message_id: The generated message id.
            msg: The message object to persist.
            segments: The wire-format segments to store as metadata.
        """
        from apeiria.conversation.store import append_message, ensure_session

        try:
            if isinstance(event, WebChatMessageEvent):
                await ensure_session(
                    session_id, "webchat", event.scene_type, event.scene_id
                )
            await append_message(
                session_id=session_id,
                role="bot",
                content=msg.extract_plain_text(),
                user_id=self.self_id,
                message_id=message_id,
                meta_json={"segments": segments},
            )
        except Exception:  # noqa: BLE001
            logger.opt(exception=True).debug("webchat: failed to persist outbound")
