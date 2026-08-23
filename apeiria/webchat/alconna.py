"""Register the WebChat adapter's UniMessage exporter and builder with Alconna."""

import base64
from typing import Any, cast

from nonebot.adapters import Bot, Event
from nonebot.adapters import Message as BaseMessage
from nonebot.log import logger
from nonebot_plugin_alconna.uniseg.builder import MessageBuilder, build
from nonebot_plugin_alconna.uniseg.constraint import SupportAdapter
from nonebot_plugin_alconna.uniseg.exporter import MessageExporter, Target, export
from nonebot_plugin_alconna.uniseg.segment import Image, Text

from apeiria.webchat.message import Message, MessageSegment


class WebChatExporter(MessageExporter[Message]):
    """Export UniMessage as a WebChat Message (text/image) and send it via bot.send."""

    def get_message_type(self) -> type[Message]:
        """Return the message class this exporter produces."""
        return Message

    @classmethod
    def get_adapter(cls) -> SupportAdapter:
        """Return the adapter identifier for the WebChat exporter."""
        return cast("SupportAdapter", "WebChat")

    def get_message_id(self, event: Event) -> str:
        """Extract the message id from an event.

        Args:
            event: The event containing the message id.

        Returns:
            The message id, or an empty string when absent.
        """
        return getattr(event, "message_id", "")

    @export
    async def text(self, seg: Text, bot: Bot | None) -> MessageSegment:  # noqa: ARG002
        """Convert a text segment into a WebChat text segment.

        Args:
            seg: The incoming text segment.
            bot: The bot instance (unused for text).

        Returns:
            A WebChat text message segment.
        """
        return MessageSegment.text(seg.text)

    @export
    async def image(self, seg: Image, bot: Bot | None) -> MessageSegment:  # noqa: ARG002
        """Convert an image segment into a WebChat image segment.

        Args:
            seg: The incoming image segment.
            bot: The bot instance (unused for images).

        Returns:
            A WebChat image message segment, using the URL or a base64 data URI.
        """
        if seg.url:
            return MessageSegment.image(url=seg.url)
        try:
            raw = seg.raw_bytes
        except (ValueError, OSError):
            return MessageSegment.raw("image", {"name": seg.name, "id": seg.id})
        mime = seg.mimetype or "image/png"
        encoded = base64.b64encode(raw).decode()
        return MessageSegment.image(base64=f"data:{mime};base64,{encoded}")

    async def send_to(
        self,
        target: Target | Event,
        bot: Bot,
        message: BaseMessage,
        **kwargs: Any,
    ) -> Any:
        """Send a message to a WebChat target.

        Args:
            target: The target event (or a proactive target).
            bot: The bot used to send the message.
            message: The message to send.
            **kwargs: Extra send options.

        Returns:
            The send result when an event target is given, otherwise ``None``.
        """
        if isinstance(target, Event):
            return await bot.send(target, cast("Message", message), **kwargs)
        logger.warning("WebChat: proactive send_to without event is unsupported")
        return None


class WebChatBuilder(MessageBuilder):
    """Build a WebChat message into a UniMessage (text handled by the base class)."""

    @classmethod
    def get_adapter(cls) -> SupportAdapter:
        """Return the adapter identifier for the WebChat builder."""
        return cast("SupportAdapter", "WebChat")

    @build("image")
    def image(self, seg: MessageSegment) -> Image:
        """Convert a WebChat image segment into a UniMessage image.

        Args:
            seg: The WebChat image segment.

        Returns:
            A UniMessage image built from the segment's URL or base64 data.
        """
        return Image(url=seg.data.get("url") or seg.data.get("base64") or None)


def register_alconna() -> None:
    """Register the WebChat exporter and builder in Alconna's mappings."""
    from nonebot_plugin_alconna.uniseg.adapters import (
        BUILDER_MAPPING,
        EXPORTER_MAPPING,
    )

    EXPORTER_MAPPING["WebChat"] = WebChatExporter()
    BUILDER_MAPPING["WebChat"] = WebChatBuilder()
    logger.success("WebChat alconna exporter/builder registered")
