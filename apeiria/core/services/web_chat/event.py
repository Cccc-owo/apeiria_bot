"""Event types for WebChat."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nonebot.adapters import Event

if TYPE_CHECKING:
    from .message import WebChatMessage
    from .session import ChatSession


class WebChatMessageEvent(Event):
    session: "ChatSession"
    message: "WebChatMessage"
    message_id: str
    time: int
    self_id: str
    post_type: str
    message_type: str
    user_id: str

    def __init__(
        self,
        *,
        session: "ChatSession",
        message: "WebChatMessage",
        message_id: str,
        timestamp: int,
        self_id: str = "webchat",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, "session", session)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "message_id", message_id)
        object.__setattr__(self, "time", timestamp)
        object.__setattr__(self, "self_id", self_id)
        object.__setattr__(self, "post_type", "message")
        object.__setattr__(self, "message_type", "private")
        object.__setattr__(self, "user_id", session.target_user_id)

    def get_type(self) -> str:
        return "message"

    def get_event_name(self) -> str:
        return "message.private"

    def get_event_description(self) -> str:
        return f"WebUI chat: {self.get_plaintext()}"

    def get_message(self) -> "WebChatMessage":
        return self.message

    def get_plaintext(self) -> str:
        return str(self.message)

    def get_user_id(self) -> str:
        return self.user_id

    def get_session_id(self) -> str:
        return self.session.target_user_id

    def is_tome(self) -> bool:
        return True
