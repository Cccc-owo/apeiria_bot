from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from nonebot.log import logger

from apeiria.web.auth import verify_token

router = APIRouter(prefix="/api/update", dependencies=[Depends(verify_token)])

_DIRTY_BLOCK_MESSAGE = "工作区存在未提交的变更，请先处理后重试"


class _UpdateError(RuntimeError):
    pass


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


async def _do_rollback(
    original_branch: str,
    original_commit: str,
    cwd: Path,
) -> None:
    logger.warning("Rolling back to {} ({})", original_branch, original_commit[:7])
    await _run_git("checkout", original_branch, cwd=cwd)
    await _run_git("reset", "--hard", original_commit, cwd=cwd)
    logger.info("Rollback complete")


async def _fetch_with_warning(*args: str, label: str = "Fetch") -> str:
    rc, _, stderr = await _run_git("fetch", *args)
    if rc != 0:
        message = f"{label} 失败: {stderr}"
        logger.warning("{}", message)
        return message
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


async def _rollback_and_error(
    original_branch: str,
    original_commit: str,
    project_root: Path,
    message: str,
) -> AsyncIterator[str]:
    await _do_rollback(original_branch, original_commit, project_root)
    yield _sse({"stage": "error", "line": message})


async def _sync_and_restart(
    project_root: Path,
    ref_type: str,
    branch: str,
) -> AsyncIterator[str]:
    uv = shutil.which("uv")
    if uv is None:
        raise _UpdateError("系统中未找到 uv 命令")  # noqa: TRY003

    yield _sse({"stage": "sync", "line": "$ uv sync"})
    proc = await asyncio.create_subprocess_exec(
        uv,
        "sync",
        cwd=project_root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    if proc.stdout is not None:
        async for line in proc.stdout:
            yield _sse(
                {
                    "stage": "sync",
                    "line": line.decode(errors="replace").rstrip(),
                }
            )
    await proc.wait()
    if proc.returncode != 0:
        raise _UpdateError(f"uv sync 返回码: {proc.returncode}")  # noqa: TRY003

    yield _sse({"stage": "done", "line": "更新完成，即将重启..."})
    logger.success("Git update to {} '{}' completed. Restarting...", ref_type, branch)

    from apeiria.utils.restart import graceful_restart

    await asyncio.sleep(0.8)
    await graceful_restart()


async def _execute_update(  # noqa: C901, PLR0912, PLR0915
    branch: str,
    commit: str | None = None,
    ref_type: str = "branch",
) -> AsyncIterator[str]:
    project_root = Path.cwd()

    rc, dirty, _ = await _run_git("status", "--porcelain")
    if rc == 0 and dirty:
        yield _sse({"stage": "error", "line": _DIRTY_BLOCK_MESSAGE})
        return

    _, original_commit, _ = await _run_git("rev-parse", "HEAD")
    _, original_branch, _ = await _run_git("branch", "--show-current")
    logger.info(
        "Starting update to {} '{}' commit '{}' from {} ({})",
        ref_type,
        branch,
        commit or "HEAD",
        original_branch,
        original_commit[:7],
    )

    try:
        if ref_type == "tag":
            yield _sse({"stage": "checkout", "line": "$ git fetch origin --tags"})
            rc_fetch, _, fetch_err = await _run_git("fetch", "origin", "--tags")
            if rc_fetch != 0:
                yield _sse({"stage": "error", "line": f"Fetch tags 失败: {fetch_err}"})
                return

            target = commit or branch
            yield _sse({"stage": "checkout", "line": f"$ git checkout {target}"})
            rc2, out, err = await _run_git("checkout", target)
            if rc2 != 0:
                async for event in _rollback_and_error(
                    original_branch,
                    original_commit,
                    project_root,
                    f"Checkout 失败: {err}",
                ):
                    yield event
                return
            for line in out.splitlines():
                if line.strip():
                    yield _sse({"stage": "checkout", "line": line})
            for line in err.splitlines():
                if line.strip():
                    yield _sse({"stage": "checkout", "line": line})
        else:
            yield _sse({"stage": "checkout", "line": f"$ git checkout {branch}"})
            rc2, out, err = await _run_git("checkout", branch)
            if rc2 != 0:
                err_stderr = await _run_git(
                    "checkout", "-b", branch, f"origin/{branch}"
                )
                if err_stderr[0] != 0:
                    msg = f"Checkout 失败: {err_stderr[2]}"
                    yield _sse({"stage": "error", "line": msg})
                    return
                out = f"Switched to a new branch '{branch}'"
            for line in out.splitlines():
                if line.strip():
                    yield _sse({"stage": "checkout", "line": line})
            for line in err.splitlines():
                if line.strip():
                    yield _sse({"stage": "checkout", "line": line})

            yield _sse({"stage": "pull", "line": f"$ git fetch origin {branch}"})
            rc3, _, fetch_err = await _run_git("fetch", "origin", branch)
            if rc3 != 0:
                async for event in _rollback_and_error(
                    original_branch,
                    original_commit,
                    project_root,
                    f"Fetch 失败: {fetch_err}",
                ):
                    yield event
                return

            target_ref = commit or f"origin/{branch}"
            yield _sse({"stage": "pull", "line": f"$ git reset --hard {target_ref}"})
            rc4, reset_out, reset_err = await _run_git("reset", "--hard", target_ref)
            for line in reset_out.splitlines():
                if line.strip():
                    yield _sse({"stage": "pull", "line": line})
            for line in reset_err.splitlines():
                if line.strip():
                    yield _sse({"stage": "pull", "line": line})
            if rc4 != 0:
                async for event in _rollback_and_error(
                    original_branch,
                    original_commit,
                    project_root,
                    f"Reset 失败: {reset_err}",
                ):
                    yield event
                return

        async for event in _sync_and_restart(
            project_root,
            ref_type,
            branch,
        ):
            yield event
    except _UpdateError as exc:
        async for event in _rollback_and_error(
            original_branch,
            original_commit,
            project_root,
            str(exc),
        ):
            yield event
    except asyncio.CancelledError:
        async for event in _rollback_and_error(
            original_branch,
            original_commit,
            project_root,
            "更新已取消，正在回滚",
        ):
            yield event
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("更新流程异常，正在回滚")
        async for event in _rollback_and_error(
            original_branch,
            original_commit,
            project_root,
            f"更新失败: {exc}",
        ):
            yield event


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

    return StreamingResponse(
        _execute_update(branch, commit=commit, ref_type=ref_type),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
