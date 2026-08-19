from __future__ import annotations

from contextlib import suppress
from typing import Protocol

from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.log import logger
from nonebot_plugin_alconna import Target, UniMessage

from .models import PendingRequest, ProcResult, RequestInfo, RequestKind


class RequestProvider(Protocol):
    key: str

    def supports(self, bot: Bot, event: Event) -> bool: ...

    def extract(self, bot: Bot, event: Event) -> RequestInfo | None: ...

    async def approve(
        self, bot: Bot, pending: PendingRequest, remark: str = ""
    ) -> ProcResult: ...

    async def reject(
        self, bot: Bot, pending: PendingRequest, reason: str = ""
    ) -> ProcResult: ...

    async def notify(
        self, bot: Bot, pending: PendingRequest, target_id: str, message: str
    ) -> str | None: ...


def _safe_str(obj: object, attr: str) -> str:
    with suppress(Exception):
        v = getattr(obj, attr, None)
        if v is not None:
            return str(v)
    return ""


class BaseFriendshipProvider:
    key: str
    adapter_name: str
    platform_name: str

    def supports(self, bot: Bot, event: Event) -> bool:
        if bot.adapter.get_name() != self.adapter_name:
            return False
        with suppress(Exception):
            return event.get_type() == "request"
        return False

    def extract(self, bot: Bot, event: Event) -> RequestInfo | None:  # noqa: ARG002
        kind = self._request_kind(event)
        if kind is None:
            return None

        requester_id = _safe_str(event, "user_id")
        if not requester_id:
            return None

        flag = _safe_str(event, "flag")
        if not flag:
            return None

        group_id = self._group_id(event)
        sub_type = _safe_str(event, "sub_type") or None
        return RequestInfo(
            kind=kind,
            requester_id=requester_id,
            requester_name=requester_id,
            platform=self.platform_name,
            raw_flag=flag,
            group_id=group_id,
            comment=_safe_str(event, "comment"),
            sub_type=sub_type if kind != "friend" else None,
        )

    def _request_kind(self, event: Event) -> RequestKind | None:
        raise NotImplementedError

    def _group_id(self, event: Event) -> str | None:
        return _safe_str(event, "group_id") or None

    async def approve(
        self, bot: Bot, pending: PendingRequest, remark: str = ""
    ) -> ProcResult:
        api, kwargs = self._approve_request(pending, remark)
        return await self._call_api(bot, api, **kwargs)

    async def reject(
        self, bot: Bot, pending: PendingRequest, reason: str = ""
    ) -> ProcResult:
        api, kwargs = self._reject_request(pending, reason)
        return await self._call_api(bot, api, **kwargs)

    def _approve_request(
        self, pending: PendingRequest, remark: str
    ) -> tuple[str, dict[str, object]]:
        raise NotImplementedError

    def _reject_request(
        self, pending: PendingRequest, reason: str
    ) -> tuple[str, dict[str, object]]:
        raise NotImplementedError

    async def _call_api(self, bot: Bot, api: str, **kwargs: object) -> ProcResult:
        try:
            await bot.call_api(api, **kwargs)
            return ProcResult(success=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("{} request failed: {}", self.key, exc)
            return ProcResult(success=False, message=str(exc))

    async def notify(
        self, bot: Bot, pending: PendingRequest, target_id: str, message: str
    ) -> str | None:
        try:
            target = Target(
                id=target_id,
                private=True,
                self_id=str(getattr(bot, "self_id", "")),
                scope=pending.scope,
                adapter=bot.adapter.get_name(),
            )
            receipt = await UniMessage(message).send(target=target, bot=bot)
            return str(receipt.msg_ids[0]) if receipt.msg_ids else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("{} notify failed: {}", self.key, exc)
            return None


class OneBotStyleFriendshipProvider(BaseFriendshipProvider):
    def _request_kind(self, event: Event) -> RequestKind | None:
        request_type = _safe_str(event, "request_type")
        sub_type = _safe_str(event, "sub_type")
        if request_type == "friend":
            return "friend"
        if request_type == "group" and sub_type == "add":
            return "group_add"
        if request_type == "group" and sub_type == "invite":
            return "group_invite"
        return None

    def _approve_request(
        self, pending: PendingRequest, remark: str
    ) -> tuple[str, dict[str, object]]:
        if pending.kind == "friend":
            return (
                "set_friend_add_request",
                {"flag": pending.raw_flag, "approve": True, "remark": remark},
            )
        return (
            "set_group_add_request",
            {
                "flag": pending.raw_flag,
                "sub_type": pending.sub_type or "add",
                "approve": True,
            },
        )

    def _reject_request(
        self, pending: PendingRequest, reason: str
    ) -> tuple[str, dict[str, object]]:
        if pending.kind == "friend":
            return (
                "set_friend_add_request",
                {"flag": pending.raw_flag, "approve": False},
            )
        return (
            "set_group_add_request",
            {
                "flag": pending.raw_flag,
                "sub_type": pending.sub_type or "add",
                "approve": False,
                "reason": reason,
            },
        )


class OneBotV11FriendshipProvider(OneBotStyleFriendshipProvider):
    key = "onebot_v11"
    adapter_name = "OneBot V11"
    platform_name = "OneBot V11"

    async def notify(
        self,
        bot: Bot,
        pending: PendingRequest,  # noqa: ARG002
        target_id: str,
        message: str,
    ) -> str | None:
        result = await bot.send_private_msg(user_id=int(target_id), message=message)
        if isinstance(result, dict):
            msg_id = result.get("message_id", "")
            return str(msg_id) if msg_id else None
        return None


_SATORI_APPROVE_API = "handle_friend_request"
_SATORI_GUILD_API = "handle_guild_request"


class SatoriFriendshipProvider(BaseFriendshipProvider):
    key = "satori"
    adapter_name = "Satori"
    platform_name = "Satori"

    def _request_kind(self, event: Event) -> RequestKind | None:
        request_type = _safe_str(event, "request_type")
        if request_type == "friend":
            return "friend"
        if request_type in ("guild", "guild-member"):
            return "group_add"
        return None

    def _group_id(self, event: Event) -> str | None:
        return _safe_str(event, "guild_id") or _safe_str(event, "group_id") or None

    def _approve_request(
        self, pending: PendingRequest, remark: str
    ) -> tuple[str, dict[str, object]]:
        api = _SATORI_APPROVE_API if pending.kind == "friend" else _SATORI_GUILD_API
        return (
            api,
            {
                "message_id": pending.raw_flag,
                "approve": True,
                "comment": remark,
            },
        )

    def _reject_request(
        self, pending: PendingRequest, reason: str
    ) -> tuple[str, dict[str, object]]:
        api = _SATORI_APPROVE_API if pending.kind == "friend" else _SATORI_GUILD_API
        return (
            api,
            {
                "message_id": pending.raw_flag,
                "approve": False,
                "comment": reason,
            },
        )


class MilkyFriendshipProvider(OneBotStyleFriendshipProvider):
    key = "milky"
    adapter_name = "nonebot-adapter-milky"
    platform_name = "nonebot-adapter-milky"


_providers: list[RequestProvider] = [
    OneBotV11FriendshipProvider(),
    SatoriFriendshipProvider(),
    MilkyFriendshipProvider(),
]


def resolve_provider(bot: Bot, event: Event) -> RequestProvider | None:
    for p in _providers:
        with suppress(Exception):
            if p.supports(bot, event):
                return p
    return None


def get_provider_by_key(key: str) -> RequestProvider | None:
    for p in _providers:
        if p.key == key:
            return p
    return None
