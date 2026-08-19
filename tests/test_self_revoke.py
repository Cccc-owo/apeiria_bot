from __future__ import annotations

from types import SimpleNamespace


def test_event_message_id_prefers_message_id() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import _event_message_id

    class Event:
        message_id = "m1"
        id = "event_id"

    assert _event_message_id(Event()) == "m1"


def test_event_message_id_falls_back_to_id() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import _event_message_id

    class Event:
        id = "msg_id"

    assert _event_message_id(Event()) == "msg_id"


def test_event_message_id_missing_returns_none() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import _event_message_id

    class Event:
        pass

    assert _event_message_id(Event()) is None


def test_qq_guild_provider_supports_fake_event() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import QQGuildRevokeProvider

    provider = QQGuildRevokeProvider()

    class Bot:
        adapter = SimpleNamespace(get_name=lambda: "QQ")
        self_id = "bot_id"

    class Reply:
        id = "reply_id"
        author = SimpleNamespace(id="bot_id")

    class Event:
        __type__ = SimpleNamespace(value="MESSAGE_CREATE")
        reply = Reply()
        channel_id = "ch"
        id = "current_id"

    assert provider.supports(Bot(), Event()) is True


def test_discord_provider_supports_fake_event() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import DiscordRevokeProvider

    provider = DiscordRevokeProvider()

    class Bot:
        adapter = SimpleNamespace(get_name=lambda: "Discord")
        self_id = "bot_id"

    class Reply:
        id = "reply_id"
        author = SimpleNamespace(id="bot_id")

    class Event:
        reply = Reply()
        channel_id = "ch"
        id = "current_id"

    assert provider.supports(Bot(), Event()) is True


async def test_base_provider_revoke_message_calls_api() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import (
        BaseApiRevokeProvider,
        RevokeTarget,
    )

    class FakeProvider(BaseApiRevokeProvider):
        adapter_name = "Fake"
        revoke_api = "delete_message"

        def _delete_kwargs(self, _event, message_id: str) -> dict[str, object]:
            return {"channel_id": "ch", "message_id": message_id}

    class Bot:
        adapter = SimpleNamespace(get_name=lambda: "Fake")
        calls: list[tuple[str, dict]]

        async def call_api(self, api: str, **kwargs: object) -> None:
            self.calls.append((api, kwargs))

    provider = FakeProvider()
    bot = Bot()
    bot.calls = []
    result = await provider.revoke_message(
        bot, SimpleNamespace(), RevokeTarget(message_id="m1", author_id="bot")
    )

    assert result.success is True
    assert bot.calls == [("delete_message", {"channel_id": "ch", "message_id": "m1"})]


async def test_base_provider_revoke_trigger_uses_event_message_id() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import BaseApiRevokeProvider

    class FakeProvider(BaseApiRevokeProvider):
        adapter_name = "Fake"
        revoke_api = "delete_message"

        def _delete_kwargs(self, _event, message_id: str) -> dict[str, object]:
            return {"message_id": message_id}

    class Bot:
        adapter = SimpleNamespace(get_name=lambda: "Fake")
        calls: list[tuple[str, dict]]

        async def call_api(self, api: str, **kwargs: object) -> None:
            self.calls.append((api, kwargs))

    class Event:
        id = "current_id"

    provider = FakeProvider()
    bot = Bot()
    bot.calls = []
    result = await provider.revoke_trigger_message(bot, Event())

    assert result.success is True
    assert bot.calls == [("delete_message", {"message_id": "current_id"})]


async def test_base_provider_apply_feedback_unsupported() -> None:
    from apeiria.builtin_plugins.self_revoke.providers import BaseApiRevokeProvider

    class FakeProvider(BaseApiRevokeProvider):
        adapter_name = "Fake"
        revoke_api = "delete_message"

        def _delete_kwargs(self, _event, message_id: str) -> dict[str, object]:
            return {"message_id": message_id}

    result = await FakeProvider().apply_feedback(
        SimpleNamespace(), SimpleNamespace(), kind="success"
    )
    assert result.success is False
    assert result.reason == "reaction_feedback_unsupported"
