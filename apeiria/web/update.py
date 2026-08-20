from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from apeiria.jobs.git_update import GitUpdateJob
from apeiria.jobs.runtime import get_job_runner
from apeiria.web.auth import verify_token

router = APIRouter(prefix="/api/update", dependencies=[Depends(verify_token)])

_job_runner = get_job_runner()


async def _run_git(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    if cwd is None:
        cwd = Path.cwd()
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return (
        proc.returncode or 0,
        stdout.decode(errors="replace").strip(),
        stderr.decode(errors="replace").strip(),
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _branch_list(output: str) -> list[str]:
    branches: list[str] = []
    for raw in output.splitlines():
        stripped = raw.strip()
        if not stripped or "->" in stripped:
            continue
        if stripped.startswith("origin/"):
            branches.append(stripped[len("origin/") :])
        else:
            branches.append(stripped)
    return sorted(set(branches))


@router.get("/status")
async def update_status() -> JSONResponse:
    rc, branch, _ = await _run_git("branch", "--show-current")
    if rc != 0 or not branch:
        raise HTTPException(status_code=500, detail="无法获取当前分支")

    _, commit_hash, _ = await _run_git("rev-parse", "--short", "HEAD")
    _, commit_message, _ = await _run_git("log", "-1", "--format=%s")

    _, dirty_output, _ = await _run_git("status", "--porcelain")
    is_dirty = bool(dirty_output)
    dirty_files = dirty_output.splitlines() if dirty_output else []

    await _fetch_with_warning("origin", "--prune", "--tags", label="刷新远端引用")

    _, branches_output, _ = await _run_git("branch", "-r")
    available_branches = _branch_list(branches_output)

    _, tags_output, _ = await _run_git("tag")
    available_tags = sorted(t.strip() for t in tags_output.splitlines() if t.strip())

    return JSONResponse(
        content={
            "branch": branch,
            "commit_hash": commit_hash,
            "commit_message": commit_message,
            "is_dirty": is_dirty,
            "dirty_files": dirty_files,
            "available_branches": available_branches,
            "available_tags": available_tags,
        }
    )


@router.get("/preview/{ref}")
async def update_preview(
    ref: str,
    ref_type: Annotated[str, Query(alias="type", pattern="^(branch|tag)$")] = "branch",
) -> JSONResponse:
    (
        log_ref,
        remote_hash,
        remote_msg,
        commits_behind,
        fetch_warning,
    ) = await _resolve_preview_ref(ref, ref_type)
    commits, local_only_commits, has_diverged = await _build_commit_list(log_ref)

    return JSONResponse(
        content={
            "ref": ref,
            "type": ref_type,
            "remote_commit_hash": remote_hash,
            "remote_commit_message": remote_msg,
            "commits_behind": commits_behind,
            "commits": commits,
            "local_only_commits": local_only_commits,
            "has_diverged": has_diverged,
            "fetch_warning": fetch_warning,
        }
    )


async def _fetch_with_warning(*args: str, label: str = "Fetch") -> str:
    rc, _, stderr = await _run_git("fetch", *args)
    if rc != 0:
        return f"{label} 失败: {stderr}"
    return ""


async def _resolve_preview_ref(
    ref: str,
    ref_type: str,
) -> tuple[str, str, str, int, str]:
    if ref_type == "tag":
        fetch_warning = await _fetch_with_warning(
            "origin", "--tags", label="Fetch tags"
        )
        tag_ref = ref
        rc, _, _ = await _run_git("rev-parse", "--short", tag_ref)
        if rc != 0:
            if fetch_warning:
                raise HTTPException(status_code=500, detail=fetch_warning)
            raise HTTPException(status_code=404, detail=f"标签 '{ref}' 不存在")

        _, remote_hash, _ = await _run_git("rev-parse", "--short", tag_ref)
        _, remote_msg, _ = await _run_git("log", "-1", "--format=%s", tag_ref)
    else:
        fetch_warning = await _fetch_with_warning("origin", ref)
        remote_ref = f"origin/{ref}"
        rc, _, _ = await _run_git("rev-parse", "--short", remote_ref)
        if rc != 0:
            if fetch_warning:
                raise HTTPException(status_code=500, detail=fetch_warning)
            raise HTTPException(status_code=404, detail=f"远端不存在分支 '{ref}'")

        _, remote_hash, _ = await _run_git("rev-parse", "--short", remote_ref)
        _, remote_msg, _ = await _run_git("log", "-1", "--format=%s", remote_ref)
        tag_ref = remote_ref

    _, behind_str, _ = await _run_git("rev-list", "--count", f"HEAD..{tag_ref}")
    commits_behind = int(behind_str) if behind_str else 0
    return tag_ref, remote_hash, remote_msg, commits_behind, fetch_warning


async def _build_commit_list(
    log_ref: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], bool]:
    _, log_out, _ = await _run_git(
        "log",
        log_ref,
        "--format=%H|%h|%s|%an|%aI",
        "-n",
        "20",
    )

    commits: list[dict[str, object]] = []
    _parts_count = 5
    for line in log_out.splitlines():
        parts = line.split("|", 4)
        if len(parts) == _parts_count:
            commits.append(
                {
                    "full_hash": parts[0],
                    "hash": parts[1],
                    "message": parts[2],
                    "author": parts[3],
                    "date": parts[4],
                }
            )

    _, local_full, _ = await _run_git("rev-parse", "HEAD")

    _, ahead_out, _ = await _run_git("rev-list", log_ref, "--not", "HEAD")
    ahead_hashes = set(ahead_out.splitlines())
    _, local_only_out, _ = await _run_git(
        "log",
        "HEAD",
        "--not",
        log_ref,
        "--format=%H|%h|%s|%an|%aI",
        "-n",
        "20",
    )

    for commit in commits:
        full_hash = commit.pop("full_hash")
        if full_hash in ahead_hashes:
            commit["direction"] = "ahead"
        elif full_hash == local_full:
            commit["direction"] = "current"
        else:
            commit["direction"] = "behind"
        commit["is_current"] = full_hash == local_full

    commits = [
        commit for commit in commits if commit["direction"] in {"ahead", "current"}
    ]

    local_only_commits: list[dict[str, object]] = []
    for line in local_only_out.splitlines():
        parts = line.split("|", 4)
        if len(parts) == _parts_count:
            local_only_commits.append(
                {
                    "hash": parts[1],
                    "message": parts[2],
                    "author": parts[3],
                    "date": parts[4],
                    "direction": "local_only",
                    "is_current": False,
                }
            )

    has_diverged = bool(ahead_hashes) and bool(local_only_out.strip())
    return commits, local_only_commits, has_diverged


@router.post("/execute")
async def update_execute(request: Request) -> StreamingResponse:
    try:
        body = await request.json()
    except json.JSONDecodeError as err:
        raise HTTPException(status_code=400, detail="请求体无效 JSON") from err

    branch = body.get("branch")
    if not branch or not isinstance(branch, str):
        raise HTTPException(status_code=400, detail="缺少或无效的 'branch' 字段")

    commit = body.get("commit")
    if commit is not None and not isinstance(commit, str):
        raise HTTPException(status_code=400, detail="无效的 'commit' 字段")

    ref_type = body.get("type", "branch")
    if ref_type not in ("branch", "tag"):
        raise HTTPException(status_code=400, detail="'type' 必须是 'branch' 或 'tag'")

    job = GitUpdateJob(branch, commit=commit, ref_type=ref_type)
    queue = job.subscribe()
    task_id = await _job_runner.start(job)

    async def event_stream():
        try:
            yield _sse({"type": "task", "task_id": task_id})
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield _sse(payload)
                if payload.get("type") in ("done", "error", "cancelled"):
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
