"""WebChat message and message segment types for the adapter."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, override

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment


class MessageSegment(BaseMessageSegment["Message"]):
    """A WebChat message segment of type text, image, or raw."""

    @classmethod
    @override
    def get_message_class(cls) -> type[Message]:
        """Return the message class that contains this segment type."""
        return Message

    @override
    def __str__(self) -> str:
        """Return a plain-text representation of the segment."""
        if self.type == "text":
            return self.data.get("text", "")
        if self.type == "image":
            return "[image]"
        if self.type == "raw":
            return f"[{self.data.get('seg_type', 'raw')}]"
        return f"[{self.type}]"

    @override
    def is_text(self) -> bool:
        """Return whether the segment is a text segment."""
        return self.type == "text"

    @classmethod
    def text(cls, text: str) -> MessageSegment:
        """Build a text segment from a string.

        Args:
            text: The text content.

        Returns:
            A new WebChat text segment.
        """
        return cls("text", {"text": text})

    @classmethod
    def image(
        cls, *, url: str | None = None, base64: str | None = None
    ) -> MessageSegment:
        """Build an image segment from a URL or a base64 data string.

        Args:
            url: The image URL.
            base64: The image data as a base64 string.

        Returns:
            A new WebChat image segment.
        """
        return cls("image", {"url": url, "base64": base64})

    @classmethod
    def raw(cls, seg_type: str, data: dict[str, Any]) -> MessageSegment:
        """Build a raw debug segment that carries an arbitrary payload.

        Args:
            seg_type: The original segment type.
            data: The raw payload data.

        Returns:
            A new WebChat raw segment.
        """
        return cls("raw", {"seg_type": seg_type, "data": data})


class Message(BaseMessage[MessageSegment]):
    """A sequence of WebChat message segments."""

    @classmethod
    @override
    def get_segment_class(cls) -> type[MessageSegment]:
        """Return the segment class used by this message."""
        return MessageSegment

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        """Yield a single text segment for a non-empty source string.

        Args:
            msg: The source string to construct from.

        Yields:
            A text segment for non-empty input.
        """
        if msg:
            yield MessageSegment.text(msg)
