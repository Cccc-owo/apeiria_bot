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
