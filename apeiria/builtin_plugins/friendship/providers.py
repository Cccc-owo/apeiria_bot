"""Friendship request providers for the built-in friendship plugin.

Translate friendship and group request events into provider-specific
approve/reject API calls for each supported adapter.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Protocol

from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.log import logger
from nonebot_plugin_alconna import Target, UniMessage

from .models import PendingRequest, ProcResult, RequestInfo, RequestKind


class RequestProvider(Protocol):
    """Interface for a friendship request provider.

    Defines the contract a concrete adapter provider implements to recognize,
    extract, approve, reject, and notify about requests.
    """

    key: str

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether this provider handles the given event."""
        ...

    def extract(self, bot: Bot, event: Event) -> RequestInfo | None:
        """Extract request information from the given event.

        Returns:
            The extracted request info, or None when the event is not a
            supported request.
        """
        ...

    async def approve(
        self, bot: Bot, pending: PendingRequest, remark: str = ""
    ) -> ProcResult:
        """Approve the given pending request.

        Args:
            bot: The bot instance to use.
            pending: The pending request to approve.
            remark: Optional remark included with the approval.

        Returns:
            The result of the approval operation.
        """
        ...

    async def reject(
        self, bot: Bot, pending: PendingRequest, reason: str = ""
    ) -> ProcResult:
        """Reject the given pending request.

        Args:
            bot: The bot instance to use.
            pending: The pending request to reject.
            reason: Optional reason included with the rejection.

        Returns:
            The result of the rejection operation.
        """
        ...

    async def notify(
        self, bot: Bot, pending: PendingRequest, target_id: str, message: str
    ) -> str | None:
        """Send a notification about the given pending request.

        Args:
            bot: The bot instance to use.
            pending: The pending request being notified about.
            target_id: The id of the target to notify.
            message: The notification message to send.

        Returns:
            The id of the sent message, or None when sending fails.
        """
        ...


def _safe_str(obj: object, attr: str) -> str:
    """Return ``str(getattr(obj, attr))``, or ``""`` if it is unavailable.

    Args:
        obj: The object to read the attribute from.
        attr: The attribute name to read.

    Returns:
        The stringified attribute value, or ``""`` on any failure.
    """
    with suppress(Exception):
        v = getattr(obj, attr, None)
        if v is not None:
            return str(v)
    return ""


class BaseFriendshipProvider:
    """Shared implementation for concrete friendship request providers."""

    key: str
    adapter_name: str
    platform_name: str

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether this provider handles the given event.

        Checks that the bot's adapter and the event type match this provider.

        Args:
            bot: The bot instance associated with the event.
            event: The incoming event to inspect.

        Returns:
            True when this provider can process the event, False otherwise.
        """
        if bot.adapter.get_name() != self.adapter_name:
            return False
        with suppress(Exception):
            return event.get_type() == "request"
        return False

    def extract(self, bot: Bot, event: Event) -> RequestInfo | None:  # noqa: ARG002
        """Extract request information from the given event.

        Builds a RequestInfo when the event carries the request kind,
        requester id, and flag this provider needs.

        Args:
            bot: The bot instance associated with the event.
            event: The incoming request event.

        Returns:
            The extracted request info, or None when required fields are
            missing.
        """
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
        """Determine the request kind from the given event.

        Args:
            event: The incoming request event.

        Returns:
            The request kind, or None when it cannot be determined.
        """
        raise NotImplementedError

    def _group_id(self, event: Event) -> str | None:
        """Return the group id from the given event.

        Args:
            event: The incoming request event.

        Returns:
            The group id, or None when the event carries no group id.
        """
        return _safe_str(event, "group_id") or None

    async def approve(
        self, bot: Bot, pending: PendingRequest, remark: str = ""
    ) -> ProcResult:
        """Approve the given pending request via the provider's API.

        Args:
            bot: The bot instance to use.
            pending: The pending request to approve.
            remark: Optional remark included with the approval.

        Returns:
            The result of the approval API call.
        """
        api, kwargs = self._approve_request(pending, remark)
        return await self._call_api(bot, api, **kwargs)

    async def reject(
        self, bot: Bot, pending: PendingRequest, reason: str = ""
    ) -> ProcResult:
        """Reject the given pending request via the provider's API.

        Args:
            bot: The bot instance to use.
            pending: The pending request to reject.
            reason: Optional reason included with the rejection.

        Returns:
            The result of the rejection API call.
        """
        api, kwargs = self._reject_request(pending, reason)
        return await self._call_api(bot, api, **kwargs)

    def _approve_request(
        self, pending: PendingRequest, remark: str
    ) -> tuple[str, dict[str, object]]:
        """Return the API name and kwargs for approving a request.

        Args:
            pending: The pending request to approve.
            remark: Optional remark included with the approval.

        Returns:
            A tuple of the API name and the keyword arguments to call it with.
        """
        raise NotImplementedError

    def _reject_request(
        self, pending: PendingRequest, reason: str
    ) -> tuple[str, dict[str, object]]:
        """Return the API name and kwargs for rejecting a request.

        Args:
            pending: The pending request to reject.
            reason: Optional reason included with the rejection.

        Returns:
            A tuple of the API name and the keyword arguments to call it with.
        """
        raise NotImplementedError

    async def _call_api(self, bot: Bot, api: str, **kwargs: object) -> ProcResult:
        """Call the given bot API and wrap the outcome.

        Args:
            bot: The bot instance to use.
            api: The name of the API to call.
            **kwargs: The keyword arguments passed to the API.

        Returns:
            A ProcResult describing whether the API call succeeded.
        """
        try:
            await bot.call_api(api, **kwargs)
            return ProcResult(success=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("{} request failed: {}", self.key, exc)
            return ProcResult(success=False, message=str(exc))

    async def notify(
        self, bot: Bot, pending: PendingRequest, target_id: str, message: str
    ) -> str | None:
        """Send a notification message to the given target.

        Args:
            bot: The bot instance to use.
            pending: The pending request being notified about.
            target_id: The id of the target to notify.
            message: The notification message to send.

        Returns:
            The id of the sent message, or None when sending fails.
        """
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
    """A friendship provider for OneBot-style adapters."""

    def _request_kind(self, event: Event) -> RequestKind | None:
        """Determine the request kind from a OneBot-style event.

        Args:
            event: The incoming request event.

        Returns:
            The request kind, or None when it is not a supported request.
        """
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
        """Return the OneBot API name and kwargs for approving a request.

        Args:
            pending: The pending request to approve.
            remark: Optional remark included with the approval.

        Returns:
            A tuple of the API name and the keyword arguments to call it with.
        """
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
        """Return the OneBot API name and kwargs for rejecting a request.

        Args:
            pending: The pending request to reject.
            reason: Optional reason included with the rejection.

        Returns:
            A tuple of the API name and the keyword arguments to call it with.
        """
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
    """A friendship provider for the OneBot V11 adapter."""

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
        """Send a private notification message for the pending request.

        Args:
            bot: The bot instance to use.
            pending: The pending request being notified about.
            target_id: The id of the target to notify.
            message: The notification message to send.

        Returns:
            The id of the sent message, or None when sending fails.
        """
        result = await bot.send_private_msg(user_id=int(target_id), message=message)
        if isinstance(result, dict):
            msg_id = result.get("message_id", "")
            return str(msg_id) if msg_id else None
        return None


_SATORI_APPROVE_API = "handle_friend_request"
_SATORI_GUILD_API = "handle_guild_request"


class SatoriFriendshipProvider(BaseFriendshipProvider):
    """A friendship provider for the Satori adapter."""

    key = "satori"
    adapter_name = "Satori"
    platform_name = "Satori"

    def _request_kind(self, event: Event) -> RequestKind | None:
        """Determine the request kind from a Satori-style event.

        Args:
            event: The incoming request event.

        Returns:
            The request kind, or None when it is not a supported request.
        """
        request_type = _safe_str(event, "request_type")
        if request_type == "friend":
            return "friend"
        if request_type in ("guild", "guild-member"):
            return "group_add"
        return None

    def _group_id(self, event: Event) -> str | None:
        """Return the guild or group id from a Satori-style event.

        Args:
            event: The incoming request event.

        Returns:
            The guild or group id, or None when not present.
        """
        return _safe_str(event, "guild_id") or _safe_str(event, "group_id") or None

    def _approve_request(
        self, pending: PendingRequest, remark: str
    ) -> tuple[str, dict[str, object]]:
        """Return the Satori API name and kwargs for approving a request.

        Args:
            pending: The pending request to approve.
            remark: Optional remark included with the approval.

        Returns:
            A tuple of the API name and the keyword arguments to call it with.
        """
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
        """Return the Satori API name and kwargs for rejecting a request.

        Args:
            pending: The pending request to reject.
            reason: Optional reason included with the rejection.

        Returns:
            A tuple of the API name and the keyword arguments to call it with.
        """
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
    """A friendship provider for the nonebot-adapter-milky adapter."""

    key = "milky"
    adapter_name = "nonebot-adapter-milky"
    platform_name = "nonebot-adapter-milky"


_providers: list[RequestProvider] = [
    OneBotV11FriendshipProvider(),
    SatoriFriendshipProvider(),
    MilkyFriendshipProvider(),
]


def resolve_provider(bot: Bot, event: Event) -> RequestProvider | None:
    """Return the first provider that supports the given event.

    Args:
        bot: The bot instance associated with the event.
        event: The incoming event to match.

    Returns:
        The matching provider, or None when no provider supports the event.
    """
    for p in _providers:
        with suppress(Exception):
            if p.supports(bot, event):
                return p
    return None


def get_provider_by_key(key: str) -> RequestProvider | None:
    """Return the provider registered under the given key.

    Args:
        key: The provider key to look up.

    Returns:
        The matching provider, or None when no provider has that key.
    """
    for p in _providers:
        if p.key == key:
            return p
    return None
