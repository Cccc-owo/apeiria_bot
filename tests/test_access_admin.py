from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


class _FakeGate:
    def __init__(self) -> None:
        self.session = _FakeSession()

    @asynccontextmanager
    async def write(self):
        yield self.session

    @asynccontextmanager
    async def read(self):
        yield self.session


async def test_add_rule_reloads_access_control(monkeypatch) -> None:
    from apeiria.builtin_plugins.admin import access_admin

    fake_gate = _FakeGate()
    monkeypatch.setattr(
        access_admin,
        "get_db",
        lambda: SimpleNamespace(gate=fake_gate),
    )

    reloaded: list[str] = []

    async def _fake_reload() -> None:
        reloaded.append("reload")

    monkeypatch.setattr(access_admin, "_reload_access", _fake_reload)

    result = await access_admin._add_rule("allow", "user", "u1", "global", "0")

    assert result.startswith("已添加")
    assert reloaded == ["reload"]
