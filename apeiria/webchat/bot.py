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
    """WebChat Bot：把出站消息序列化回推浏览器，并做 webchat 范围出站持久化。"""

    def __init__(
        self,
        adapter: Adapter,
        self_id: str,
        connections: ConnectionManager,
    ) -> None:
        super().__init__(adapter, self_id)
        self.connections = connections

    async def send(
        self,
        event: Event,
        message: str | BaseMessage | BaseMessageSegment,
        **kwargs: Any,  # noqa: ARG002
    ) -> Any:
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
