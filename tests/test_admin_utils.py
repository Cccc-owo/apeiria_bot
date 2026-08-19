from __future__ import annotations

from types import SimpleNamespace


def _bot():
    return SimpleNamespace()


def _event():
    return SimpleNamespace(get_user_id=lambda: "123")


async def test_is_owner_event_uses_native_superuser(monkeypatch) -> None:
    from apeiria.builtin_plugins.admin import utils

    async def _true(_bot, _event) -> bool:
        return True

    monkeypatch.setattr(utils, "SUPERUSER", _true)
    assert await utils.is_owner_event(_bot(), _event()) is True


async def test_is_owner_event_false_when_native_superuser_false(monkeypatch) -> None:
    from apeiria.builtin_plugins.admin import utils

    async def _false(_bot, _event) -> bool:
        return False

    monkeypatch.setattr(utils, "SUPERUSER", _false)
    assert await utils.is_owner_event(_bot(), _event()) is False


async def test_ensure_owner_message_returns_none_for_owner(monkeypatch) -> None:
    from apeiria.builtin_plugins.admin import utils

    async def _true(_bot, _event) -> bool:
        return True

    monkeypatch.setattr(utils, "SUPERUSER", _true)
    assert await utils.ensure_owner_message(_bot(), _event()) is None


async def test_ensure_owner_message_returns_hint_for_non_owner(monkeypatch) -> None:
    from apeiria.builtin_plugins.admin import utils

    async def _false(_bot, _event) -> bool:
        return False

    monkeypatch.setattr(utils, "SUPERUSER", _false)
    assert await utils.ensure_owner_message(_bot(), _event()) == "仅限超级用户使用"
