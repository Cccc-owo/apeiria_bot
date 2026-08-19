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
        "branch -r": (0, "  origin/main\n  origin/dev\n", ""),
        "tag": (0, "v1\nv2", ""),
    }

    async def fake_run_git(*args: str, **_kwargs: object) -> tuple[int, str, str]:
        return responses.get(" ".join(args), (0, "", ""))

    monkeypatch.setattr(update, "_run_git", fake_run_git)

    resp = await update.update_status()
    assert resp.status_code == 200
    data = json.loads(resp.body)
    assert data["available_branches"] == ["dev", "main"]
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
