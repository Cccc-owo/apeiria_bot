from __future__ import annotations

from types import SimpleNamespace


def _pending(kind: str, sub_type: str | None = None):
    from apeiria.builtin_plugins.friendship.models import PendingRequest

    return PendingRequest(
        id="f1",
        provider_key="test",
        bot_self_id="1",
        scope="Test",
        raw_flag="flag",
        kind=kind,
        requester_id="2",
        requester_name="requester",
        sub_type=sub_type,
    )


async def test_onebot_approve_friend_uses_call_api() -> None:
    from apeiria.builtin_plugins.friendship.providers import (
        OneBotV11FriendshipProvider,
    )

    calls: list[tuple[str, dict]] = []

    async def call_api(api: str, **kwargs: object) -> None:
        calls.append((api, kwargs))

    bot = SimpleNamespace(call_api=call_api)
    provider = OneBotV11FriendshipProvider()

    result = await provider.approve(bot, _pending("friend"), remark="hello")

    assert result.success is True
    assert calls == [
        (
            "set_friend_add_request",
            {"flag": "flag", "approve": True, "remark": "hello"},
        )
    ]


async def test_onebot_reject_group_uses_call_api() -> None:
    from apeiria.builtin_plugins.friendship.providers import (
        OneBotV11FriendshipProvider,
    )

    calls: list[tuple[str, dict]] = []

    async def call_api(api: str, **kwargs: object) -> None:
        calls.append((api, kwargs))

    bot = SimpleNamespace(call_api=call_api)
    provider = OneBotV11FriendshipProvider()

    result = await provider.reject(
        bot, _pending("group_add", sub_type="add"), reason="no"
    )

    assert result.success is True
    assert calls == [
        (
            "set_group_add_request",
            {
                "flag": "flag",
                "sub_type": "add",
                "approve": False,
                "reason": "no",
            },
        )
    ]


async def test_satori_approve_guild_uses_handle_guild_request() -> None:
    from apeiria.builtin_plugins.friendship.providers import (
        SatoriFriendshipProvider,
    )

    calls: list[tuple[str, dict]] = []

    async def call_api(api: str, **kwargs: object) -> None:
        calls.append((api, kwargs))

    bot = SimpleNamespace(call_api=call_api)
    provider = SatoriFriendshipProvider()

    result = await provider.approve(bot, _pending("group_add"), remark="welcome")

    assert result.success is True
    assert calls == [
        (
            "handle_guild_request",
            {"message_id": "flag", "approve": True, "comment": "welcome"},
        )
    ]
