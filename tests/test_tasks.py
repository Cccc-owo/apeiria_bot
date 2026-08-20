from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_run_task_emits_error_on_unexpected_exception() -> None:
    from apeiria.web import tasks

    runner = tasks.TaskRunner()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def boom() -> None:
        raise RuntimeError("boom")

    await runner._run_task(queue, boom())

    event = queue.get_nowait()
    assert event["type"] == "error"
    assert event["ok"] is False
    assert "boom" in event["message"]
    assert queue.empty()


@pytest.mark.asyncio
async def test_sync_manifest_env_reports_failure(monkeypatch) -> None:
    from apeiria.web import tasks

    runner = tasks.TaskRunner()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def fake_run_subprocess(
        _queue: asyncio.Queue[dict], _uv: str, *args: str
    ) -> int:
        assert args == ("sync",)
        return 1

    monkeypatch.setattr(runner, "_run_subprocess", fake_run_subprocess)

    ok = await runner._sync_manifest_env(queue, "/usr/bin/uv")

    assert ok is False
    events = [queue.get_nowait() for _ in range(queue.qsize())]
    assert any(
        event["type"] == "error" and "uv sync 返回码" in event["message"]
        for event in events
    )


@pytest.mark.asyncio
async def test_finished_task_queue_is_removed_after_cleanup_delay(
    monkeypatch,
) -> None:
    from apeiria.web import tasks

    monkeypatch.setattr(tasks, "_TASK_CLEANUP_DELAY", 0.01)
    monkeypatch.setattr(tasks.shutil, "which", lambda _name: None)

    runner = tasks.TaskRunner()
    task_id = await runner.start("plugin", "demo")
    assert task_id in runner._queues

    await asyncio.sleep(0.03)
    assert task_id not in runner._queues
