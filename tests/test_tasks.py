from __future__ import annotations

import asyncio

import pytest

from apeiria.jobs.base import Job, JobRunner, JobStatus


class _BoomJob(Job):
    def __init__(self) -> None:
        super().__init__(kind="boom")

    async def run(self) -> None:
        raise RuntimeError("boom")


class _DoneJob(Job):
    def __init__(self) -> None:
        super().__init__(kind="done")

    async def run(self) -> None:
        self.emit({"type": "output", "text": "hello"})


class _BlockingJob(Job):
    def __init__(self, release: asyncio.Event) -> None:
        super().__init__(kind="block", lock_name="apeiria")
        self.release = release

    async def run(self) -> None:
        await self.release.wait()


async def _wait_terminal(runner: JobRunner, job_id: str, max_wait: float = 2.0) -> dict:
    deadline = asyncio.get_running_loop().time() + max_wait
    while asyncio.get_running_loop().time() < deadline:
        status = await runner.get_status(job_id)
        if status and status["status"] in (
            JobStatus.DONE.value,
            JobStatus.ERROR.value,
            JobStatus.CANCELLED.value,
        ):
            return status
        await asyncio.sleep(0.01)
    msg = "job did not reach terminal status"
    raise AssertionError(msg)


@pytest.mark.asyncio
async def test_runner_emits_error_on_unexpected_exception() -> None:
    runner = JobRunner()
    job = _BoomJob()
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(
        event["type"] == "error" and "boom" in event["message"] for event in events
    )
    status = await runner.get_status(job_id)
    assert status is not None
    assert status["status"] == JobStatus.ERROR.value


@pytest.mark.asyncio
async def test_runner_done_emits_done_event() -> None:
    runner = JobRunner()
    job = _DoneJob()
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(
        event["type"] == "output" and event["text"] == "hello" for event in events
    )
    assert any(event["type"] == "done" for event in events)


@pytest.mark.asyncio
async def test_cancel_pending_job_before_lock() -> None:
    runner = JobRunner()
    release = asyncio.Event()
    first = _BlockingJob(release)
    first_id = await runner.start(first)

    second = _BlockingJob(release)
    second_queue = second.subscribe()
    second_id = await runner.start(second)
    # Let the second task reach the lock wait.
    await asyncio.sleep(0.05)

    assert await runner.cancel(second_id) is True
    await _wait_terminal(runner, second_id)

    events = []
    while not second_queue.empty():
        events.append(second_queue.get_nowait())
    assert any(event["type"] == "cancelled" for event in events)
    status = await runner.get_status(second_id)
    assert status is not None
    assert status["status"] == JobStatus.CANCELLED.value

    release.set()
    await _wait_terminal(runner, first_id)


@pytest.mark.asyncio
async def test_finished_job_queue_is_removed_after_cleanup_delay(
    monkeypatch,
) -> None:
    from apeiria.jobs import base

    monkeypatch.setattr(base, "_JOB_CLEANUP_DELAY", 0.01)

    runner = JobRunner()
    job = _DoneJob()
    job_id = await runner.start(job)

    # The job is very fast; wait for the cleanup delay to remove it.
    await asyncio.sleep(0.05)
    assert job_id not in runner.jobs


@pytest.mark.asyncio
async def test_package_uninstall_rollback_restores_plugin_dir(
    tmp_path, monkeypatch
) -> None:
    from apeiria.jobs import package as package_mod
    from apeiria.jobs.package import PackageJob

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".apeiria" / "plugins" / "demo").mkdir(parents=True)
    (tmp_path / ".apeiria" / "plugins" / "demo" / "__init__.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    (tmp_path / ".apeiria" / "plugins.yaml").write_text(
        "packages:\n  demo: demo-pkg\nstates: {}\n", encoding="utf-8"
    )
    (tmp_path / ".apeiria" / "adapters.yaml").write_text(
        "packages: {}\nstates: {}\n", encoding="utf-8"
    )
    (tmp_path / ".apeiria" / "pyproject.toml").write_text(
        "[project]\n", encoding="utf-8"
    )
    (tmp_path / ".apeiria" / "uv.lock").write_text("lock\n", encoding="utf-8")

    async def fake_remove(_job: object, _req: str, _cwd: object) -> int:
        return 0

    async def fake_sync(_job: object, _cwd: object) -> int:
        return 1

    monkeypatch.setattr(package_mod, "run_uv_remove", fake_remove)
    monkeypatch.setattr(package_mod, "run_uv_sync", fake_sync)

    runner = JobRunner()
    job = PackageJob("plugin", "demo", "demo-pkg", operation="uninstall")
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(event["type"] == "error" for event in events)
    assert (tmp_path / ".apeiria" / "plugins" / "demo" / "__init__.py").exists()
    manifest_text = (tmp_path / ".apeiria" / "plugins.yaml").read_text(encoding="utf-8")
    assert "demo" in manifest_text
