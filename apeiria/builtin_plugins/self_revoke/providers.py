# ruff: noqa: ARG002
"""Provider implementations for the self-revoke plugin across adapters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import ClassVar, Literal, Protocol, cast

from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.log import logger

FeedbackKind = Literal["success", "failure"]


def _string_attr(obj: object, name: str) -> str | None:
    """Return the string value of an attribute if present, else ``None``.

    Args:
        obj (object): Object to inspect.
        name (str): Attribute name to read.

    Returns:
        str | None: The attribute value as a string, or ``None`` if missing.
    """
    with suppress(Exception):
        value = getattr(obj, name, None)
        if value is not None:
            return str(value)
    return None


def _nested_string_attr(obj: object, *names: str) -> str | None:
    """Traverse nested attributes and return the final value as a string.

    Args:
        obj (object): Starting object.
        *names (str): Attribute names to traverse in order.

    Returns:
        str | None: The final value as a string, or ``None`` if missing.
    """
    for name in names:
        obj = getattr(obj, name, None) if obj is not None else None
    if obj is not None:
        return str(obj)
    return None


def _event_message_id(event: Event) -> str | None:
    """Extract a message ID from an event using adapter-specific fields.

    Args:
        event (Event): The incoming event.

    Returns:
        str | None: The message ID as a string, or ``None`` if not found.
    """
    mid = _string_attr(event, "message_id")
    if mid is not None:
        return mid
    with suppress(Exception):
        getter = getattr(event, "get_message_id", None)
        if callable(getter):
            value = getter()
            if value is not None:
                return str(value)
    # QQ Guild / Discord 等适配器的消息 ID 直接放在 id 字段。
    return _string_attr(event, "id")


def _message_id_value(message_id: str) -> int | str:
    """Coerce a message ID to an integer when possible, else return the string.

    Args:
        message_id (str): The message ID string.

    Returns:
        int | str: The message ID as an integer, or the original string when
        it cannot be parsed.
    """
    try:
        return int(message_id)
    except (TypeError, ValueError):
        return message_id


@dataclass(frozen=True, slots=True)
class RevokeTarget:
    """Identifies a message to revoke and, optionally, its author."""

    message_id: str
    author_id: str | None = None


class RevokeActionResult:
    """Outcome and reason of a revocation attempt."""

    __slots__ = ("reason", "success")

    def __init__(self, *, success: bool = False, reason: str = "") -> None:
        """Initialize the result with a success flag and a reason.

        Args:
            success (bool, optional): Whether the revocation succeeded.
                Defaults to ``False``.
            reason (str, optional): Human-readable reason string.
                Defaults to an empty string.
        """
        self.success = success
        self.reason = reason

    @classmethod
    def ok(cls) -> "RevokeActionResult":
        """Create a successful result.

        Returns:
            RevokeActionResult: A result with ``success`` set to ``True``.
        """
        return cls(success=True)

    @classmethod
    def failed(cls, reason: str = "operation_failed") -> "RevokeActionResult":
        """Create a failed result with an optional reason.

        Args:
            reason (str, optional): Reason for the failure.
                Defaults to ``"operation_failed"``.

        Returns:
            RevokeActionResult: A result with ``success`` set to ``False``.
        """
        return cls(success=False, reason=reason)

    @classmethod
    def unsupported(cls, reason: str = "unsupported") -> "RevokeActionResult":
        """Create an unsupported result with an optional reason.

        Args:
            reason (str, optional): Reason for the unsupported operation.
                Defaults to ``"unsupported"``.

        Returns:
            RevokeActionResult: A result with ``success`` set to ``False``.
        """
        return cls(success=False, reason=reason)


class SelfRevokeProvider(Protocol):
    """Interface implemented by adapter-specific revocation providers."""

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether this provider handles the given event.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if this provider can handle the event.
        """
        ...

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event, if one exists.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        ...

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the target message was authored by the bot.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        ...

    async def revoke_message(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> RevokeActionResult:
        """Revoke the target message.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The message to revoke.

        Returns:
            RevokeActionResult: The outcome of the revocation attempt.
        """
        ...

    async def revoke_trigger_message(
        self, bot: Bot, event: Event
    ) -> RevokeActionResult:
        """Revoke the message that triggered the event.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeActionResult: The outcome of the revocation attempt.
        """
        ...

    async def apply_feedback(
        self, bot: Bot, event: Event, *, kind: FeedbackKind
    ) -> RevokeActionResult:
        """Apply feedback to the message that triggered the event.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            kind (FeedbackKind): Feedback kind to apply.

        Returns:
            RevokeActionResult: The outcome of the feedback operation.
        """
        ...


_revoke_providers: list[SelfRevokeProvider] = []


def _register_provider(provider: SelfRevokeProvider) -> None:
    """Register a provider instance in the global provider registry.

    Args:
        provider (SelfRevokeProvider): Provider instance to register.
    """
    _revoke_providers.append(provider)


def _resolve_provider(bot: Bot, event: Event) -> SelfRevokeProvider | None:
    """Return the first registered provider that supports the given event.

    Args:
        bot (Bot): The bot instance handling the event.
        event (Event): The incoming event.

    Returns:
        SelfRevokeProvider | None: The matching provider, or ``None`` if none
        supports the event.
    """
    for provider in _revoke_providers:
        with suppress(Exception):
            if provider.supports(bot, event):
                return provider
    return None


async def _call_api(bot: Bot, api: str, **data: object) -> RevokeActionResult:
    """Call a bot API and wrap the outcome as a :class:`RevokeActionResult`.

    Args:
        bot (Bot): The bot instance on which to call the API.
        api (str): The API name to invoke.
        **data (object): Keyword arguments forwarded to the API call.

    Returns:
        RevokeActionResult: A successful result on success, or a failed result
        carrying the error message on failure.
    """
    try:
        await bot.call_api(api, **data)
        return RevokeActionResult.ok()
    except Exception as exc:  # noqa: BLE001
        return RevokeActionResult.failed(str(exc))


class BaseApiRevokeProvider:
    """Base class that shares the revocation API call logic across adapters.

    Subclasses must provide:
    - ``adapter_name``: the adapter name.
    - ``revoke_api``: the revocation API name, usable with ``{message_id}``
      as a path template.
    - ``_delete_kwargs(event, message_id)``: build the revocation request
      arguments.
    """

    adapter_name: ClassVar[str]
    revoke_api: ClassVar[str]
    missing_delete_data_reason: ClassVar[str] = "chat_id_missing"

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether this provider matches the configured adapter name.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event comes from the configured adapter.
        """
        return bot.adapter.get_name() == self.adapter_name

    async def revoke_message(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> RevokeActionResult:
        """Revoke the target message via the adapter's revocation API.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The message to revoke.

        Returns:
            RevokeActionResult: The outcome of the revocation attempt.
        """
        kwargs = self._delete_kwargs(event, target.message_id)
        if kwargs is None:
            return RevokeActionResult.unsupported(self.missing_delete_data_reason)
        api = self.revoke_api.format(message_id=target.message_id)
        return await _call_api(bot, api, **kwargs)

    async def revoke_trigger_message(
        self, bot: Bot, event: Event
    ) -> RevokeActionResult:
        """Revoke the message that triggered the event.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeActionResult: The outcome of the revocation attempt.
        """
        message_id = self._trigger_message_id(event)
        if message_id is None:
            return RevokeActionResult.unsupported("trigger_message_id_missing")
        kwargs = self._delete_kwargs(event, message_id)
        if kwargs is None:
            return RevokeActionResult.unsupported(self.missing_delete_data_reason)
        api = self.revoke_api.format(message_id=message_id)
        return await _call_api(bot, api, **kwargs)

    def _trigger_message_id(self, event: Event) -> str | None:
        """Return the trigger message ID from the event.

        Args:
            event (Event): The incoming event.

        Returns:
            str | None: The message ID as a string, or ``None`` if missing.
        """
        return _event_message_id(event)

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object] | None:
        """Build the revocation request arguments for the adapter.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object] | None: The API request arguments, or ``None``
            when required data is missing.

        Raises:
            NotImplementedError: Always raised in the base class.
        """
        raise NotImplementedError

    async def apply_feedback(
        self, bot: Bot, event: Event, *, kind: FeedbackKind
    ) -> RevokeActionResult:
        """Apply feedback to the trigger message when supported.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            kind (FeedbackKind): Feedback kind to apply.

        Returns:
            RevokeActionResult: An ``unsupported`` result by default.
        """
        return RevokeActionResult.unsupported("reaction_feedback_unsupported")


# -- OneBot V11 provider --

_ONEBOT_V11_NAME = "OneBot V11"
_ONEBOT_SUCCESS_EMOJI = "124"
_ONEBOT_FAILURE_EMOJI = "424"


class OneBotV11RevokeProvider(BaseApiRevokeProvider):
    """Revoke messages and apply reaction feedback for the OneBot V11 adapter."""

    adapter_name = _ONEBOT_V11_NAME
    revoke_api = "delete_msg"
    _EMOJI_MAP: ClassVar[dict[FeedbackKind, str]] = {
        "success": _ONEBOT_SUCCESS_EMOJI,
        "failure": _ONEBOT_FAILURE_EMOJI,
    }

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a OneBot V11 reply with a message ID.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on OneBot V11.
        """
        if bot.adapter.get_name() != _ONEBOT_V11_NAME:
            return False
        return hasattr(event, "reply") and hasattr(event, "message_id")

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for OneBot V11.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply", None)
        if reply is None:
            return None
        message_id = _string_attr(reply, "message_id")
        if message_id is None:
            return None
        author_id = None
        sender = getattr(reply, "sender", None)
        if sender is not None:
            author_id = _string_attr(sender, "user_id")
        return RevokeTarget(message_id=message_id, author_id=author_id)

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on OneBot V11.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        bot_ids = {
            str(item)
            for item in (
                getattr(bot, "self_id", None),
                getattr(event, "self_id", None),
            )
            if item is not None
        }
        return target.author_id is not None and target.author_id in bot_ids

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object]:
        """Build the ``delete_msg`` request arguments.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object]: The API request arguments.
        """
        return {"message_id": _message_id_value(message_id)}

    async def apply_feedback(
        self, bot: Bot, event: Event, *, kind: FeedbackKind
    ) -> RevokeActionResult:
        """React to the trigger message with an emoji on OneBot V11.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            kind (FeedbackKind): Feedback kind to apply.

        Returns:
            RevokeActionResult: The outcome of the feedback operation.
        """
        message_id = _event_message_id(event)
        if message_id is None:
            return RevokeActionResult.unsupported("trigger_message_id_missing")
        emoji_id = self._EMOJI_MAP[kind]
        return await _call_api(
            bot,
            "set_msg_emoji_like",
            message_id=_message_id_value(message_id),
            emoji_id=emoji_id,
        )


_register_provider(OneBotV11RevokeProvider())

# -- OneBot V12 provider --

_ONEBOT_V12_NAME = "OneBot V12"


class OneBotV12RevokeProvider(BaseApiRevokeProvider):
    """Revoke messages for the OneBot V12 adapter."""

    adapter_name = _ONEBOT_V12_NAME
    revoke_api = "delete_message"

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a OneBot V12 reply with a message ID.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on OneBot V12.
        """
        if bot.adapter.get_name() != _ONEBOT_V12_NAME:
            return False
        return hasattr(event, "reply") and hasattr(event, "message_id")

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for OneBot V12.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply", None)
        if reply is None:
            return None
        message_id = _string_attr(reply, "message_id")
        if message_id is None:
            return None
        return RevokeTarget(
            message_id=message_id,
            author_id=_string_attr(reply, "user_id"),
        )

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on OneBot V12.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        bot_self_id = _string_attr(bot, "self_id")
        event_self_id = _nested_string_attr(event, "self", "user_id")
        return (
            target.author_id is not None
            and bot_self_id is not None
            and event_self_id is not None
            and bot_self_id == event_self_id == target.author_id
        )

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object]:
        """Build the ``delete_message`` request arguments.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object]: The API request arguments.
        """
        return {"message_id": message_id}


_register_provider(OneBotV12RevokeProvider())

# -- Telegram provider --

_TELEGRAM_NAME = "Telegram"


class TelegramRevokeProvider(BaseApiRevokeProvider):
    """Revoke messages for the Telegram adapter."""

    adapter_name = _TELEGRAM_NAME
    revoke_api = "delete_message"

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a revocable Telegram reply to a message.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on Telegram.
        """
        if bot.adapter.get_name() != _TELEGRAM_NAME:
            return False
        reply = getattr(event, "reply_to_message", None)
        return (
            reply is not None
            and _string_attr(reply, "message_id") is not None
            and _nested_string_attr(reply, "from_", "id") is not None
            and _nested_string_attr(event, "chat", "id") is not None
            and _string_attr(event, "message_id") is not None
        )

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for Telegram.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply_to_message", None)
        if reply is None:
            return None
        message_id = _string_attr(reply, "message_id")
        author_id = _nested_string_attr(reply, "from_", "id")
        if message_id is None or author_id is None:
            return None
        return RevokeTarget(message_id=message_id, author_id=author_id)

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on Telegram.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        bot_id_raw = getattr(bot, "self_id", None)
        if bot_id_raw is None:
            return False
        bot_id = str(bot_id_raw)
        return (
            target.author_id is not None
            and bot_id is not None
            and target.author_id == bot_id
        )

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object] | None:
        """Build the ``delete_message`` request arguments for Telegram.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object] | None: The API request arguments, or ``None``
            when the chat ID is missing.
        """
        chat_id = _nested_string_attr(event, "chat", "id")
        if chat_id is None:
            return None
        return {
            "chat_id": _message_id_value(chat_id),
            "message_id": _message_id_value(message_id),
        }


_register_provider(TelegramRevokeProvider())

# -- Discord provider --

_DISCORD_NAME = "Discord"


class DiscordRevokeProvider(BaseApiRevokeProvider):
    """Revoke messages for the Discord adapter."""

    adapter_name = _DISCORD_NAME
    revoke_api = "delete_message"

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a revocable Discord reply.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on Discord.
        """
        if bot.adapter.get_name() != _DISCORD_NAME:
            return False
        reply = getattr(event, "reply", None)
        return (
            reply is not None
            and _string_attr(reply, "id") is not None
            and _nested_string_attr(reply, "author", "id") is not None
            and _string_attr(event, "channel_id") is not None
            and _event_message_id(event) is not None
        )

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for Discord.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply", None)
        if reply is None:
            return None
        message_id = _string_attr(reply, "id")
        author_id = _nested_string_attr(reply, "author", "id")
        if message_id is None or author_id is None:
            return None
        return RevokeTarget(message_id=message_id, author_id=author_id)

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on Discord.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        bot_ids = {
            str(item).strip()
            for item in (
                getattr(bot, "self_id", None),
                _nested_string_attr(bot, "self_info", "id"),
            )
            if item is not None and str(item).strip()
        }
        return target.author_id is not None and target.author_id in bot_ids

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object] | None:
        """Build the ``delete_message`` request arguments for Discord.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object] | None: The API request arguments, or ``None``
            when the channel ID is missing.
        """
        channel_id = _string_attr(event, "channel_id")
        if channel_id is None:
            return None
        return {"channel_id": channel_id, "message_id": message_id}


_register_provider(DiscordRevokeProvider())

# -- Feishu provider --

_FEISHU_NAME = "Feishu"


class FeishuRevokeProvider(BaseApiRevokeProvider):
    """Revoke messages for the Feishu (Lark) adapter."""

    adapter_name = _FEISHU_NAME
    revoke_api = "im/v1/messages/{message_id}"

    def _bot_app_id(self, bot: Bot) -> str | None:
        """Return the bot application ID for Feishu.

        Args:
            bot (Bot): The bot instance handling the event.

        Returns:
            str | None: The bot application ID, or ``None`` if missing.
        """
        return _nested_string_attr(bot, "bot_config", "app_id") or _string_attr(
            bot, "self_id"
        )

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a revocable Feishu reply.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on Feishu.
        """
        if bot.adapter.get_name() != _FEISHU_NAME:
            return False
        reply = getattr(event, "reply", None)
        return (
            reply is not None
            and _string_attr(reply, "message_id") is not None
            and _nested_string_attr(reply, "sender", "id") is not None
            and _nested_string_attr(reply, "sender", "id_type") is not None
            and self._bot_app_id(bot) is not None
            and _event_message_id(event) is not None
        )

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for Feishu.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply", None)
        if reply is None:
            return None
        message_id = _string_attr(reply, "message_id")
        author_id = _nested_string_attr(reply, "sender", "id")
        if message_id is None or author_id is None:
            return None
        return RevokeTarget(message_id=message_id, author_id=author_id)

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on Feishu.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        reply = getattr(event, "reply", None)
        sender_type = _nested_string_attr(reply, "sender", "id_type")
        bot_app_id = self._bot_app_id(bot)
        return (
            sender_type == "app_id"
            and target.author_id is not None
            and bot_app_id is not None
            and target.author_id == bot_app_id
        )

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object]:
        """Build the Feishu revocation request arguments.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object]: The API request arguments.
        """
        return {"method": "DELETE"}


_register_provider(FeishuRevokeProvider())

# -- Satori provider --

_SATORI_NAME = "Satori"


class SatoriRevokeProvider(BaseApiRevokeProvider):
    """Revoke messages for the Satori adapter."""

    adapter_name = _SATORI_NAME
    revoke_api = "message_delete"

    def _channel_id(self, event: Event) -> str | None:
        """Return the channel ID from the event.

        Args:
            event (Event): The incoming event.

        Returns:
            str | None: The channel ID, or ``None`` if missing.
        """
        return _nested_string_attr(event, "channel", "id")

    def _bot_user_id(self, bot: Bot) -> str | None:
        """Return the bot's user ID for Satori.

        Args:
            bot (Bot): The bot instance handling the event.

        Returns:
            str | None: The bot user ID, or ``None`` if missing.
        """
        getter = getattr(bot, "get_self_id", None)
        if callable(getter):
            with suppress(Exception):
                value = getter()
                if value is not None and str(value).strip():
                    return str(value).strip()
        return _nested_string_attr(bot, "self_info", "id")

    def _reply_message_id(self, reply: object) -> str | None:
        """Return the reply message ID from a reply object.

        Args:
            reply (object): The reply object to inspect.

        Returns:
            str | None: The message ID, or ``None`` if missing.
        """
        data = getattr(reply, "data", None)
        if data is not None:
            with suppress(Exception):
                mid = data.get("id")  # type: ignore[union-attr]
                if mid:
                    return str(mid)
        return _string_attr(reply, "id")

    def _reply_author_id(self, reply: object) -> str | None:
        """Return the reply author ID from a reply object.

        Args:
            reply (object): The reply object to inspect.

        Returns:
            str | None: The author ID, or ``None`` if missing.
        """
        children = getattr(reply, "children", None)
        getter = getattr(children, "get", None)
        if not callable(getter):
            return None
        try:
            author_segments = getter("author")
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(author_segments, Sequence):
            return None
        try:
            author = author_segments[0]
        except (IndexError, TypeError):
            return None
        data = getattr(author, "data", None)
        if data is not None:
            with suppress(Exception):
                aid = data.get("id")  # type: ignore[union-attr]
                if aid:
                    return str(aid)
        return _string_attr(author, "id")

    async def _fetch_author_id(
        self, bot: Bot, event: Event, message_id: str | None
    ) -> str | None:
        """Fetch the author ID of a message via the ``message_get`` API.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            message_id (str | None): The message ID to query.

        Returns:
            str | None: The author ID, or ``None`` if unavailable.
        """
        channel_id = self._channel_id(event)
        if message_id is None or channel_id is None:
            return None
        call_api = getattr(bot, "call_api", None)
        if not callable(call_api):
            return None
        try:
            message = await cast("Callable[..., Awaitable[object]]", call_api)(
                "message_get",
                channel_id=channel_id,
                message_id=message_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("撤回 Satori message_get 失败: {}", exc)
            return None
        return _nested_string_attr(message, "user", "id")

    def _msg_id(self, event: Event) -> str | None:
        """Return the trigger message ID from the event.

        Args:
            event (Event): The incoming event.

        Returns:
            str | None: The trigger message ID, or ``None`` if missing.
        """
        return (
            _string_attr(event, "msg_id")
            or _nested_string_attr(event, "message", "id")
            or _event_message_id(event)
        )

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a revocable Satori reply.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on Satori.
        """
        if bot.adapter.get_name() != _SATORI_NAME:
            return False
        reply = getattr(event, "reply", None)
        return (
            reply is not None
            and self._reply_message_id(reply) is not None
            and self._bot_user_id(bot) is not None
            and self._channel_id(event) is not None
            and self._msg_id(event) is not None
        )

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for Satori.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply", None)
        if reply is None:
            return None
        message_id = self._reply_message_id(reply)
        if message_id is None:
            return None
        author_id = self._reply_author_id(reply) or (
            await self._fetch_author_id(bot, event, message_id)
        )
        if author_id is None:
            return None
        return RevokeTarget(message_id=message_id, author_id=author_id)

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on Satori.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        bot_id_set = {
            str(item).strip()
            for item in (self._bot_user_id(bot),)
            if item is not None and str(item).strip()
        }
        return target.author_id is not None and target.author_id in bot_id_set

    def _trigger_message_id(self, event: Event) -> str | None:
        """Return the trigger message ID from the event.

        Args:
            event (Event): The incoming event.

        Returns:
            str | None: The trigger message ID, or ``None`` if missing.
        """
        return self._msg_id(event)

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object] | None:
        """Build the ``message_delete`` request arguments for Satori.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object] | None: The API request arguments, or ``None``
            when the channel ID is missing.
        """
        channel_id = self._channel_id(event)
        if channel_id is None:
            return None
        return {"channel_id": channel_id, "message_id": message_id}


_register_provider(SatoriRevokeProvider())

# -- QQ Guild provider --

_QQ_NAME = "QQ"


class QQGuildRevokeProvider(BaseApiRevokeProvider):
    """Revoke messages for the QQ Guild adapter."""

    adapter_name = _QQ_NAME
    revoke_api = "delete_message"

    def _event_type_name(self, event: Event) -> str:
        """Return the lowercased event type name.

        Args:
            event (Event): The incoming event.

        Returns:
            str: The lowercased event type name, or an empty string.
        """
        value = getattr(event, "__type__", None)
        if value is None:
            return ""
        name = getattr(value, "value", value)
        return str(name).lower()

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a revocable QQ Guild reply.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on QQ Guild.
        """
        if bot.adapter.get_name() != _QQ_NAME:
            return False
        if self._event_type_name(event) == "direct_message_create":
            return False
        reply = getattr(event, "reply", None)
        return (
            reply is not None
            and _string_attr(reply, "id") is not None
            and _nested_string_attr(reply, "author", "id") is not None
            and _string_attr(event, "channel_id") is not None
            and _event_message_id(event) is not None
        )

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for QQ Guild.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply", None)
        if reply is None:
            return None
        message_id = _string_attr(reply, "id")
        author_id = _nested_string_attr(reply, "author", "id")
        if message_id is None or author_id is None:
            return None
        return RevokeTarget(message_id=message_id, author_id=author_id)

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on QQ Guild.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        bot_ids = {
            str(item).strip()
            for item in (
                getattr(bot, "self_id", None),
                _nested_string_attr(bot, "self_info", "id"),
            )
            if item is not None and str(item).strip()
        }
        return target.author_id is not None and target.author_id in bot_ids

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object] | None:
        """Build the ``delete_message`` request arguments for QQ Guild.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object] | None: The API request arguments, or ``None``
            when the channel ID is missing.
        """
        channel_id = _string_attr(event, "channel_id")
        if channel_id is None:
            return None
        return {"channel_id": channel_id, "message_id": message_id}


_register_provider(QQGuildRevokeProvider())

# -- Milky provider --

_MILKY_NAME = "nonebot-adapter-milky"


class MilkyRevokeProvider(BaseApiRevokeProvider):
    """Revoke messages for the nonebot-adapter-milky adapter."""

    adapter_name = _MILKY_NAME
    revoke_api = "delete_msg"

    def supports(self, bot: Bot, event: Event) -> bool:
        """Return whether the event is a milky reply with a message ID.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            bool: ``True`` if the event is revocable on milky.
        """
        if bot.adapter.get_name() != _MILKY_NAME:
            return False
        return hasattr(event, "reply") and hasattr(event, "message_id")

    async def get_reply_target(self, bot: Bot, event: Event) -> RevokeTarget | None:
        """Extract the reply target from the event for milky.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.

        Returns:
            RevokeTarget | None: The referenced message, or ``None`` if the
            event is not a reply.
        """
        reply = getattr(event, "reply", None)
        if reply is None:
            return None
        message_id = _string_attr(reply, "message_id")
        if message_id is None:
            return None
        author_id = None
        sender = getattr(reply, "sender", None)
        if sender is not None:
            author_id = _string_attr(sender, "user_id")
        return RevokeTarget(message_id=message_id, author_id=author_id)

    async def is_bot_authored(
        self, bot: Bot, event: Event, target: RevokeTarget
    ) -> bool:
        """Return whether the bot authored the target message on milky.

        Args:
            bot (Bot): The bot instance handling the event.
            event (Event): The incoming event.
            target (RevokeTarget): The target message to check.

        Returns:
            bool: ``True`` if the bot authored the target message.
        """
        bot_ids = {
            str(item)
            for item in (
                getattr(bot, "self_id", None),
                getattr(event, "self_id", None),
            )
            if item is not None
        }
        return target.author_id is not None and target.author_id in bot_ids

    def _delete_kwargs(self, event: Event, message_id: str) -> dict[str, object]:
        """Build the ``delete_msg`` request arguments.

        Args:
            event (Event): The incoming event.
            message_id (str): The message ID to revoke.

        Returns:
            dict[str, object]: The API request arguments.
        """
        return {"message_id": _message_id_value(message_id)}


_register_provider(MilkyRevokeProvider())
