from __future__ import annotations

import re
import uuid
from types import SimpleNamespace


def _pending(kind: str = "friend", request_id: str = "") -> object:
    from apeiria.builtin_plugins.friendship.models import PendingRequest

    return PendingRequest(
        id=request_id,
        provider_key="onebot_v11",
        bot_self_id="1",
        scope="QQClient",
        raw_flag="flag",
        kind=kind,
        requester_id="2",
        requester_name="requester",
    )


def test_generate_id_uses_kind_prefix() -> None:
    from apeiria.builtin_plugins.friendship.pending import _generate_id

    assert re.fullmatch(r"f-[0-9a-f]{4}", _generate_id([], "friend"))
    assert re.fullmatch(r"g-[0-9a-f]{4}", _generate_id([], "group_add"))
    assert re.fullmatch(r"g-[0-9a-f]{4}", _generate_id([], "group_invite"))


def test_generate_id_retries_on_collision(monkeypatch) -> None:
    from apeiria.builtin_plugins.friendship.pending import _generate_id

    values = iter(
        [
            SimpleNamespace(hex="0000" + "0" * 28),
            SimpleNamespace(hex="0001" + "0" * 28),
        ]
    )
    monkeypatch.setattr(uuid, "uuid4", lambda: next(values))

    request_id = _generate_id([_pending(request_id="f-0000")], "friend")

    assert request_id == "f-0001"
