"""Alconna / UniSeg compatibility for WebChat."""

import base64
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from nonebot.adapters import Bot, Event, Message
from nonebot_plugin_alconna.uniseg.builder import MessageBuilder, build
from nonebot_plugin_alconna.uniseg.constraint import SupportAdapter, SupportScope
from nonebot_plugin_alconna.uniseg.exporter import MessageExporter, Target, export
from nonebot_plugin_alconna.uniseg.segment import At, Emoji, Image, Reply, Segment, Text

from .event import WebChatMessageEvent
from .message import WebChatMessage, WebChatMessageSegment


class WebChatMessageBuilder(MessageBuilder[WebChatMessageSegment]):
    @classmethod
    def get_adapter(cls) -> SupportAdapter:
        return SupportAdapter.onebot11

    @build("image")
    def image(self, seg: WebChatMessageSegment) -> Image:
        data = seg.data
        return Image(
            id=data.get("asset_id"),
            url=data.get("url"),
            raw=base64.b64decode(data["base64"]) if data.get("base64") else None,
            mimetype=data.get("mime"),
        )

    @build("mention")
    def mention(self, seg: WebChatMessageSegment) -> At | None:
        data = seg.data
        target = data.get("target")
        if not isinstance(target, str) or not target:
            return None
        mention_type = data.get("mention_type")
        flag = (
            mention_type
            if mention_type in {"user", "role", "channel"}
            else "user"
        )
        return At(
            flag=flag,
            target=target,
            display=data.get("display"),
        )

    @build("reply")
    def reply(self, seg: WebChatMessageSegment) -> Reply | None:
        data = seg.data
        message_id = data.get("message_id") or data.get("id")
        if not isinstance(message_id, str) or not message_id:
            return None
        return Reply(message_id)


class WebChatMessageExporter(MessageExporter[WebChatMessage]):
    def get_message_type(self) -> type[WebChatMessage]:
        return WebChatMessage

    @classmethod
    def get_adapter(cls) -> SupportAdapter:
        return SupportAdapter.onebot11

    def get_target(self, event: Event, bot: Bot | None = None) -> Target:
        assert isinstance(event, WebChatMessageEvent)
        return Target(
            event.get_user_id(),
            private=True,
            adapter=self.get_adapter(),
            self_id=bot.self_id if bot else None,
            scope=SupportScope.qq_client,
        )

    def get_message_id(self, event: Event) -> str:
        assert isinstance(event, WebChatMessageEvent)
        return str(event.message_id)

    @export
    async def text(self, seg: Text, _bot: Bot | None) -> WebChatMessageSegment:
        return WebChatMessageSegment.text(seg.text)

    @export
    async def media(self, seg: Image, _bot: Bot | None) -> WebChatMessageSegment:
        if seg.raw:
            return WebChatMessageSegment.image(
                base64_data=base64.b64encode(seg.raw_bytes).decode("ascii"),
                mime=seg.mimetype,
            )
        return WebChatMessageSegment.image(
            url=seg.url,
            asset_id=seg.id,
            mime=seg.mimetype,
        )

    @export
    async def at(self, seg: At, _bot: Bot | None) -> WebChatMessageSegment:
        return WebChatMessageSegment.mention(
            seg.target,
            display=seg.display,
            mention_type=seg.flag,
        )

    @export
    async def reply(self, seg: Reply, _bot: Bot | None) -> WebChatMessageSegment:
        return WebChatMessageSegment.reply(
            seg.id,
            text=str(seg.msg) if seg.msg else None,
        )

    async def send_to(
        self,
        target: Target | Event,
        bot: Bot,
        message: Message,
        **kwargs: Any,
    ) -> Any:
        if TYPE_CHECKING:
            assert hasattr(bot, "send")
        if isinstance(target, Event):
            return await bot.send(target, message, **kwargs)
        raise NotImplementedError

    async def recall(self, mid: Any, bot: Bot, context: Target | Event) -> None:
        raise NotImplementedError

    async def edit(
        self,
        new: Sequence[Segment],
        mid: Any,
        bot: Bot,
        context: Target | Event,
    ) -> None:
        raise NotImplementedError

    async def reaction(
        self,
        emoji: Emoji,
        mid: Any,
        bot: Bot,
        context: Target | Event,
        delete: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        raise NotImplementedError


def register_webchat_uniseg() -> None:
    from nonebot_plugin_alconna.uniseg.adapters import BUILDER_MAPPING, EXPORTER_MAPPING

    EXPORTER_MAPPING["WebChat"] = WebChatMessageExporter()
    BUILDER_MAPPING["WebChat"] = WebChatMessageBuilder()
