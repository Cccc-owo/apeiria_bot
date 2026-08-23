"""WebChat event models and helpers that resolve whether a message targets the bot."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import override

from nonebot.adapters import Event as BaseEvent

from apeiria.webchat.message import Message, MessageSegment


class WebChatEvent(BaseEvent):
    """Base class for WebChat events."""

    time: int
    self_id: str
    post_type: str

    @override
    def get_type(self) -> str:
        """Return the event's post type."""
        return self.post_type

    @override
    def get_event_name(self) -> str:
        """Return the event's name."""
        return self.post_type

    @override
    def get_event_description(self) -> str:
        """Return the event's description."""
        return self.post_type

    @override
    def get_user_id(self) -> str:
        """Raise because the base event carries no user id.

        Raises:
            ValueError: The base event has no user id.
        """
        raise ValueError("Event has no user_id")  # noqa: TRY003

    @override
    def get_session_id(self) -> str:
        """Raise because the base event carries no session id.

        Raises:
            ValueError: The base event has no session id.
        """
        raise ValueError("Event has no session_id")  # noqa: TRY003

    @override
    def get_message(self) -> Message:
        """Raise because the base event carries no message.

        Raises:
            ValueError: The base event has no message.
        """
        raise ValueError("Event has no message")  # noqa: TRY003

    @override
    def is_tome(self) -> bool:
        """Return whether the event is directed at the bot (always ``False`` here)."""
        return False


class WebChatMessageEvent(WebChatEvent):
    """A WebChat message event."""

    post_type: str = "message"
    message_id: str
    user_id: str
    message: Message
    scene_type: str  # "private" | "group"
    scene_id: str
    to_me: bool = False
    connection_id: str = ""

    @override
    def get_event_name(self) -> str:
        """Return the event name based on the scene type."""
        return f"message.{self.scene_type}"

    @override
    def get_event_description(self) -> str:
        """Return a human-readable description of the message event."""
        scene = "private" if self.scene_type == "private" else f"group:{self.scene_id}"
        return f"Message from {self.user_id}@{scene}: {self.get_plaintext()!r}"

    @override
    def get_user_id(self) -> str:
        """Return the id of the user that sent the message."""
        return self.user_id

    @override
    def get_session_id(self) -> str:
        """Return the webchat session id for the event's scene."""
        if self.scene_type == "group":
            return f"webchat:group:{self.scene_id}"
        return f"webchat:private:{self.user_id}"

    @override
    def get_message(self) -> Message:
        """Return the message carried by the event."""
        return self.message

    @override
    def is_tome(self) -> bool:
        """Return whether the message is directed at the bot."""
        return self.to_me


def is_at_me(
    message: Message,
    scene_type: str,
    nicknames: Iterable[str],
) -> bool:
    """Return True for private chats and detect a nickname prefix match for group chats.

    Args:
        message: The message to inspect.
        scene_type: The scene type, ``private`` or ``group``.
        nicknames: The configured bot nicknames.

    Returns:
        Whether the message is directed at the bot.
    """
    if scene_type != "group":
        return True
    names = [re.escape(n) for n in nicknames if n]
    if not names or not message or message[0].type != "text":
        return False
    text = message[0].data.get("text", "")
    return bool(re.match(rf"^(?:{'|'.join(names)})\s*", text))


def strip_at_prefix(message: Message, nicknames: Iterable[str]) -> None:
    """Strip a matched nickname prefix from the leading message segment.

    Args:
        message: The message whose prefix should be stripped.
        nicknames: The configured bot nicknames.
    """
    names = [re.escape(n) for n in nicknames if n]
    if not names or not message or message[0].type != "text":
        return
    text = message[0].data.get("text", "")
    matched = re.match(rf"^(?:{'|'.join(names)})\s*", text)
    if not matched:
        return
    message[0].data["text"] = text[matched.end() :]
    if not message[0].data["text"]:
        del message[0]
    if not message:
        message.append(MessageSegment.text(""))


def resolve_to_me(
    message: Message,
    scene_type: str,
    nicknames: Iterable[str],
) -> bool:
    """Resolve whether a message is directed at the bot, stripping the nickname prefix.

    Args:
        message: The message to resolve.
        scene_type: The scene type, ``private`` or ``group``.
        nicknames: The configured bot nicknames.

    Returns:
        Whether the message is directed at the bot.
    """
    result = is_at_me(message, scene_type, nicknames)
    if result and scene_type == "group":
        strip_at_prefix(message, nicknames)
    return result
