from __future__ import annotations

import asyncio
import json

import pytest

from apeiria.jobs.base import JobRunner, JobStatus
from apeiria.jobs.git_update import GitUpdateJob


@pytest.fixture(autouse=True)
def _reset_update_caches():
    from apeiria.web import update

    update._ref_fetch_cache.clear()
    update._refs_cache["fetched_at"] = 0.0
    yield


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
async def test_update_status_falls_back_to_local_refs(monkeypatch) -> None:
    from apeiria.web import update

    responses: dict[str, tuple[int, str, str]] = {
        "branch --show-current": (0, "main", ""),
        "rev-parse --short HEAD": (0, "abc1234", ""),
        "log -1 --format=%s": (0, "local msg", ""),
        "status --porcelain": (0, "", ""),
        "fetch origin --prune --tags": (1, "", "offline"),
        "branch -r": (0, "  origin/main\n  origin/dev\n  origin/feature\n", ""),
        "tag": (0, "v1\nv2", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    resp = await update.update_status()
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["available_branches"] == ["dev", "feature", "main"]
    assert data["available_tags"] == ["v1", "v2"]


@pytest.mark.asyncio
async def test_update_preview_falls_back_to_cached_ref(monkeypatch) -> None:
    from apeiria.web import update

    responses: dict[str, tuple[int, str, str]] = {
        "fetch origin main": (1, "", "offline"),
        "rev-parse --short origin/main": (0, "cafe123", ""),
        "log -1 --format=%s origin/main": (0, "remote msg", ""),
        "rev-list --count HEAD..origin/main": (0, "3", ""),
        "rev-list --count origin/main": (0, "42", ""),
        "log origin/main --format=%H|%h|%s|%an|%aI -n 20": (0, "", ""),
        "rev-parse --short HEAD": (0, "deadbee", ""),
        "log -1 --format=%s": (0, "local msg", ""),
        "log -1 --format=%an": (0, "author", ""),
        "log -1 --format=%aI": (0, "2026-01-01T00:00:00+08:00", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    resp = await update.update_preview("main")
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["remote_commit_hash"] == "cafe123"
    assert data["fetch_warning"] == "Fetch 失败: offline"
    assert data["total"] == 42
    assert data["offset"] == 0
    assert data["limit"] == 20


@pytest.mark.asyncio
async def test_resolve_preview_ref_tag_falls_back_to_cached_tag(monkeypatch) -> None:
    from apeiria.web import update

    responses: dict[str, tuple[int, str, str]] = {
        "fetch origin --tags": (1, "", "offline"),
        "rev-parse --short v1": (0, "beef123", ""),
        "log -1 --format=%s v1": (0, "tag msg", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    result = await update._resolve_preview_ref("v1", "tag")

    assert result == (
        "v1",
        "beef123",
        "tag msg",
        0,
        "Fetch tags 失败: offline",
    )


@pytest.mark.asyncio
async def test_build_commit_list_marks_ahead_and_current(monkeypatch) -> None:
    from apeiria.web import update

    responses: dict[str, tuple[int, str, str]] = {
        "log origin/main --format=%H|%h|%s|%an|%aI -n 20": (
            0,
            "full_abc|abc123|remote msg|author|2026-01-01T00:00:00+08:00\n"
            "full_def|def456|local msg|author|2026-01-02T00:00:00+08:00",
            "",
        ),
        "rev-parse HEAD": (0, "full_def", ""),
        "rev-list origin/main --not HEAD": (0, "full_abc", ""),
        "log HEAD --not origin/main --format=%H|%h|%s|%an|%aI -n 20": (
            0,
            "",
            "",
        ),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    commits, local_only, has_diverged = await update._build_commit_list("origin/main")

    assert len(commits) == 2
    assert commits[0]["hash"] == "abc123"
    assert commits[0]["direction"] == "ahead"
    assert commits[0]["is_current"] is False
    assert commits[1]["hash"] == "def456"
    assert commits[1]["direction"] == "current"
    assert commits[1]["is_current"] is True
    assert local_only == []
    assert has_diverged is False


@pytest.mark.asyncio
async def test_build_commit_list_detects_diverged_local_only(monkeypatch) -> None:
    from apeiria.web import update

    responses: dict[str, tuple[int, str, str]] = {
        "log origin/main --format=%H|%h|%s|%an|%aI -n 20": (
            0,
            "full_abc|abc123|remote msg|author|2026-01-01T00:00:00+08:00",
            "",
        ),
        "rev-parse HEAD": (0, "full_def", ""),
        "rev-list origin/main --not HEAD": (0, "full_abc", ""),
        "log HEAD --not origin/main --format=%H|%h|%s|%an|%aI -n 20": (
            0,
            "full_def|def456|local msg|author|2026-01-02T00:00:00+08:00",
            "",
        ),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    commits, local_only, has_diverged = await update._build_commit_list("origin/main")

    assert len(commits) == 1
    assert commits[0]["direction"] == "ahead"
    assert len(local_only) == 1
    assert local_only[0]["hash"] == "def456"
    assert local_only[0]["direction"] == "local_only"
    assert has_diverged is True


@pytest.mark.asyncio
async def test_build_commit_list_keeps_history_with_direction(monkeypatch) -> None:
    from apeiria.web import update

    responses: dict[str, tuple[int, str, str]] = {
        "log origin/main --format=%H|%h|%s|%an|%aI -n 20": (
            0,
            "full_remote|remote|remote msg|author|2026-01-01T00:00:00+08:00\n"
            "full_common|common|common msg|author|2026-01-01T00:00:00+08:00",
            "",
        ),
        "rev-parse HEAD": (0, "full_local", ""),
        "rev-list origin/main --not HEAD": (0, "full_remote", ""),
        "log HEAD --not origin/main --format=%H|%h|%s|%an|%aI -n 20": (
            0,
            "full_local|local|local msg|author|2026-01-01T00:00:00+08:00",
            "",
        ),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    commits, _, _ = await update._build_commit_list("origin/main")

    # The full history is kept (not filtered to ahead/current only), so a common
    # ancestor is still listed, tagged as "behind" (a valid rollback target).
    assert [c["hash"] for c in commits] == ["remote", "common"]
    assert commits[0]["direction"] == "ahead"
    assert commits[1]["direction"] == "behind"


@pytest.mark.asyncio
async def test_build_commit_list_paginates_with_offset(monkeypatch) -> None:
    from apeiria.web import update

    responses: dict[str, tuple[int, str, str]] = {
        "log origin/main --format=%H|%h|%s|%an|%aI --skip 20 -n 10": (
            0,
            "full_pag|pag|pag msg|author|2026-01-01T00:00:00+08:00",
            "",
        ),
        "rev-parse HEAD": (0, "full_local", ""),
        "rev-list origin/main --not HEAD": (0, "", ""),
        "log HEAD --not origin/main --format=%H|%h|%s|%an|%aI -n 20": (
            0,
            "",
            "",
        ),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    commits, _, _ = await update._build_commit_list("origin/main", offset=20, limit=10)

    assert len(commits) == 1
    assert commits[0]["hash"] == "pag"
    assert commits[0]["direction"] == "behind"


@pytest.mark.asyncio
async def test_execute_update_reset_failure_rolls_back(monkeypatch) -> None:
    from apeiria.jobs import git_update

    responses: dict[str, tuple[int, str, str]] = {
        "status --porcelain": (0, "", ""),
        "rev-parse HEAD": (0, "originalcommit", ""),
        "branch --show-current": (0, "main", ""),
        "checkout main": (0, "Already on 'main'", ""),
        "fetch origin main": (0, "", ""),
        "reset --hard origin/main": (1, "", "reset failed"),
        "reset --hard originalcommit": (0, "", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    async def fake_sync(_job: object, _cwd: object) -> int:
        return 0

    monkeypatch.setattr(git_update, "_run_git", fake_run_git)
    monkeypatch.setattr(git_update, "run_uv_sync", fake_sync)

    runner = JobRunner()
    job = GitUpdateJob("main", restart=False)
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(
        event["type"] == "error" and "Reset 失败: reset failed" in event["message"]
        for event in events
    )
    assert any(
        event.get("stage") == "rollback" and "回滚完成" in event.get("line", "")
        for event in events
    )


@pytest.mark.asyncio
async def test_execute_update_sync_failure_rolls_back(monkeypatch) -> None:
    from apeiria.jobs import git_update

    responses: dict[str, tuple[int, str, str]] = {
        "status --porcelain": (0, "", ""),
        "rev-parse HEAD": (0, "originalcommit", ""),
        "branch --show-current": (0, "main", ""),
        "checkout main": (0, "Already on 'main'", ""),
        "fetch origin main": (0, "", ""),
        "reset --hard origin/main": (0, "", ""),
        "reset --hard originalcommit": (0, "", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    async def fake_sync(_job: object, _cwd: object) -> int:
        return 1

    monkeypatch.setattr(git_update, "_run_git", fake_run_git)
    monkeypatch.setattr(git_update, "run_uv_sync", fake_sync)

    runner = JobRunner()
    job = GitUpdateJob("main", restart=False)
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(
        event["type"] == "error" and "uv sync 返回码: 1" in event["message"]
        for event in events
    )
    assert any(
        event.get("stage") == "rollback" and "回滚完成" in event.get("line", "")
        for event in events
    )


@pytest.mark.asyncio
async def test_execute_update_blocks_when_dirty_and_block_strategy(
    monkeypatch,
) -> None:
    from apeiria.jobs import git_update

    responses: dict[str, tuple[int, str, str]] = {
        "status --porcelain": (0, " M apeiria/web/update.py", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    async def fake_sync(_job: object, _cwd: object) -> int:
        return 0

    monkeypatch.setattr(git_update, "_run_git", fake_run_git)
    monkeypatch.setattr(git_update, "run_uv_sync", fake_sync)

    runner = JobRunner()
    job = GitUpdateJob("main", restart=False)
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(
        event["type"] == "error" and "工作区存在未提交" in event["message"]
        for event in events
    )


@pytest.mark.asyncio
async def test_execute_update_stash_then_restore(monkeypatch) -> None:
    from apeiria.jobs import git_update

    responses: dict[str, tuple[int, str, str]] = {
        "status --porcelain": (0, " M apeiria/web/update.py\n?? .tools/", ""),
        "rev-parse HEAD": (0, "originalcommit", ""),
        "branch --show-current": (0, "main", ""),
        "stash push --include-untracked -m apeiria-update": (
            0,
            "Saved working directory and index state",
            "",
        ),
        "checkout main": (0, "Already on 'main'", ""),
        "fetch origin main": (0, "", ""),
        "reset --hard origin/main": (0, "", ""),
        "stash pop": (0, "Dropped refs/stash@{0}", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    async def fake_sync(_job: object, _cwd: object) -> int:
        return 0

    monkeypatch.setattr(git_update, "_run_git", fake_run_git)
    monkeypatch.setattr(git_update, "run_uv_sync", fake_sync)

    runner = JobRunner()
    job = GitUpdateJob("main", restart=False, dirty_strategy="stash")
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(
        event.get("stage") == "stash" and "Saved" in event.get("line", "")
        for event in events
    )
    assert any(
        event.get("stage") == "stash" and "Dropped" in event.get("line", "")
        for event in events
    )
    assert any(event["type"] == "done" for event in events)


@pytest.mark.asyncio
async def test_execute_update_discard_proceeds(monkeypatch) -> None:
    from apeiria.jobs import git_update

    responses: dict[str, tuple[int, str, str]] = {
        "status --porcelain": (0, " M apeiria/web/update.py", ""),
        "rev-parse HEAD": (0, "originalcommit", ""),
        "branch --show-current": (0, "main", ""),
        "checkout main": (0, "Already on 'main'", ""),
        "fetch origin main": (0, "", ""),
        "reset --hard origin/main": (0, "", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    async def fake_sync(_job: object, _cwd: object) -> int:
        return 0

    monkeypatch.setattr(git_update, "_run_git", fake_run_git)
    monkeypatch.setattr(git_update, "run_uv_sync", fake_sync)

    runner = JobRunner()
    job = GitUpdateJob("main", restart=False, dirty_strategy="discard")
    queue = job.subscribe()
    job_id = await runner.start(job)
    await _wait_terminal(runner, job_id)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    # Discard strategy runs without stashing and completes.
    assert not any(event.get("stage") == "stash" for event in events)
    assert any(event["type"] == "done" for event in events)
