from __future__ import annotations

from apeiria.bootstrap.plan import BootstrapPlan


def test_run_stops_on_first_failure() -> None:
    plan = BootstrapPlan()
    calls: list[str] = []

    def ok() -> None:
        calls.append("ok")

    def boom() -> None:
        calls.append("boom")
        msg = "boom"
        raise RuntimeError(msg)

    def never() -> None:
        calls.append("never")

    plan.add_step("ok", ok)
    plan.add_step("boom", boom)
    plan.add_step("never", never)

    result = plan.run("test")

    assert calls == ["ok", "boom"]
    assert result.success == ("ok",)
    assert result.failed == ("boom",)
    assert result.ok is False
