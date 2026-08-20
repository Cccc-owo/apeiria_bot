from __future__ import annotations

import json

import pytest


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
async def test_build_commit_list_filters_common_ancestors(monkeypatch) -> None:
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

    assert [c["hash"] for c in commits] == ["remote"]


@pytest.mark.asyncio
async def test_execute_update_reset_failure_rolls_back(monkeypatch) -> None:
    from apeiria.web import update

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

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    events = [event async for event in update._execute_update("main")]

    assert any('"Reset 失败: reset failed"' in event for event in events)


@pytest.mark.asyncio
async def test_execute_update_sync_failure_rolls_back(monkeypatch) -> None:
    from apeiria.web import update

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

    async def fake_sync(*_args: object, **_kwargs: object):
        raise update._UpdateError("uv sync 返回码: 1")  # noqa: TRY003
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(update, "_run_git", fake_run_git)
    monkeypatch.setattr(update, "_sync_and_restart", fake_sync)

    events = [event async for event in update._execute_update("main")]

    assert any('"uv sync 返回码: 1"' in event for event in events)
