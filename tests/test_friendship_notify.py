from __future__ import annotations

from types import SimpleNamespace


async def test_onebot_notify_returns_message_id() -> None:
    from apeiria.builtin_plugins.friendship.models import PendingRequest
    from apeiria.builtin_plugins.friendship.providers import (
        OneBotV11FriendshipProvider,
    )

    calls: list[tuple[int, str]] = []

    async def send_private_msg(user_id: int, message: str) -> dict[str, int]:
        calls.append((user_id, message))
        return {"message_id": 42}

    bot = SimpleNamespace(send_private_msg=send_private_msg)
    pending = PendingRequest(
        id="f1",
        provider_key="onebot_v11",
        bot_self_id="1",
        scope="QQClient",
        raw_flag="flag",
        kind="friend",
        requester_id="2",
        requester_name="requester",
    )

    provider = OneBotV11FriendshipProvider()

    assert await provider.notify(bot, pending, "123", "hi") == "42"
    assert calls == [(123, "hi")]
