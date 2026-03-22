"""Bot implementation for WebChat."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from nonebot.adapters import Bot
from nonebot.log import logger

from .protocol import ErrorPayload, MessageReceivePayload

if TYPE_CHECKING:
    from .connection import WebChatConnection
    from .event import WebChatMessageEvent
    from .message import WebChatMessage, WebChatMessageSegment
    from .session import ChatSession


class WebChatBot(Bot):
    def __init__(
        self,
        adapter: Any,
        session: "ChatSession",
        connection: "WebChatConnection",
        service: Any,
    ) -> None:
        super().__init__(adapter, f"webui_{session.session_id}")
        object.__setattr__(self, "_session", session)
        object.__setattr__(self, "_connection", connection)
        object.__setattr__(self, "_service", service)

    async def send(
        self,
        event: "WebChatMessageEvent",  # noqa: ARG002
        message: str | "WebChatMessage" | "WebChatMessageSegment",
        **kwargs: Any,  # noqa: ARG002
    ) -> Any:
        segments = await self._service.codec.encode_message(message)
        payload = MessageReceivePayload(
            session_id=self._session.session_id,
            message_id=f"srv_{uuid4().hex}",
            role="bot",
            segments=segments,
            timestamp=datetime.now(UTC),
        )
        await self._service.emit_message(self._connection, payload)
        return {"status": "ok"}

    async def call_api(self, api: str, **data: Any) -> Any:
        logger.debug("Unhandled WebUI chat API call: {} {}", api, data)
        return None

    async def emit_error(self, message: str) -> None:
        await self._connection.send_envelope(
            "message.error",
            ErrorPayload(code="HANDLE_EVENT_ERROR", message=message),
        )
