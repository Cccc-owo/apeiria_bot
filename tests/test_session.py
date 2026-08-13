from __future__ import annotations

from types import SimpleNamespace

from apeiria.utils.session import (
    resolve_superuser_targets,
    scoped_group_id,
    scoped_user_id,
)


def _session(scope="QQClient", scene_id="123456", user_id="789012"):
    return SimpleNamespace(
        scope=scope,
        scene=SimpleNamespace(id=scene_id),
        user=SimpleNamespace(id=user_id),
    )


def _bot(adapter_name="OneBot V11", self_id="bot1"):
    return SimpleNamespace(
        adapter=SimpleNamespace(get_name=lambda: adapter_name),
        self_id=self_id,
    )


class TestScopedIds:
    def test_scoped_group_id(self) -> None:
        s = _session(scope="QQClient", scene_id="888888")
        assert scoped_group_id(s) == "QQClient:888888"

    def test_scoped_user_id(self) -> None:
        s = _session(scope="QQClient", user_id="123456")
        assert scoped_user_id(s) == "QQClient:123456"

    def test_scoped_group_id_telegram(self) -> None:
        s = _session(scope="Telegram", scene_id="-100123")
        assert scoped_group_id(s) == "Telegram:-100123"

    def test_scoped_user_id_telegram(self) -> None:
        s = _session(scope="Telegram", user_id="user123")
        assert scoped_user_id(s) == "Telegram:user123"


class TestResolveSuperuserTargets:
    def test_prefixed_targets(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "apeiria.utils.session.get_driver",
            lambda: SimpleNamespace(
                config=SimpleNamespace(
                    superusers={"onebot:111", "onebot:222", "telegram:333"}
                )
            ),
        )
        bot = _bot(adapter_name="OneBot V11")
        targets = resolve_superuser_targets(bot)
        assert sorted(targets) == ["111", "222"]

    def test_bare_ids_fallback(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "apeiria.utils.session.get_driver",
            lambda: SimpleNamespace(config=SimpleNamespace(superusers={"123456"})),
        )
        bot = _bot(adapter_name="OneBot V11")
        targets = resolve_superuser_targets(bot)
        assert targets == ["123456"]

    def test_mixed_prefixed_and_bare(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "apeiria.utils.session.get_driver",
            lambda: SimpleNamespace(
                config=SimpleNamespace(
                    superusers={"onebot:111", "123456", "telegram:333"}
                )
            ),
        )
        bot = _bot(adapter_name="OneBot V11")
        targets = resolve_superuser_targets(bot)
        assert sorted(targets) == ["111", "123456"]

    def test_no_matching_targets(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "apeiria.utils.session.get_driver",
            lambda: SimpleNamespace(
                config=SimpleNamespace(superusers={"telegram:333"})
            ),
        )
        bot = _bot(adapter_name="OneBot V11")
        targets = resolve_superuser_targets(bot)
        assert targets == []


def _meta_session(scope="QQClient", scene_type="GROUP", scene_id="123"):
    return SimpleNamespace(
        scope=scope,
        scene=SimpleNamespace(type=SimpleNamespace(name=scene_type), id=scene_id),
    )


def test_extract_session_meta_group_uses_uninfo() -> None:
    from apeiria.bootstrap.steps import _extract_session_meta

    event = SimpleNamespace()
    session = _meta_session()

    assert _extract_session_meta(event, "group_123_456", session) == (
        "QQClient",
        "group",
        "123",
    )


def test_extract_session_meta_private_uses_uninfo() -> None:
    from apeiria.bootstrap.steps import _extract_session_meta

    event = SimpleNamespace()
    session = _meta_session(scene_type="PRIVATE", scene_id="456")

    assert _extract_session_meta(event, "private_456", session) == (
        "QQClient",
        "private",
        "456",
    )


def test_extract_session_meta_fallback_fixes_precedence() -> None:
    from apeiria.bootstrap.steps import _extract_session_meta

    event = SimpleNamespace(message_type="private")

    assert _extract_session_meta(event, "private_456", None) == (
        "unknown",
        "private",
        "456",
    )

    def test_empty_superusers(self, monkeypatch) -> None:  # noqa: ARG001
        monkeypatch.setattr(
            "apeiria.utils.session.get_driver",
            lambda: SimpleNamespace(config=SimpleNamespace(superusers=set())),
        )
        bot = _bot(adapter_name="OneBot V11")
        targets = resolve_superuser_targets(bot)
        assert targets == []
