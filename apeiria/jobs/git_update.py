from __future__ import annotations

import asyncio
from pathlib import Path

from nonebot.log import logger

from apeiria.jobs.base import Job, JobError
from apeiria.jobs.uv import run_uv_sync

_DIRTY_BLOCK_MESSAGE = "工作区存在未提交的变更，请先处理后重试"


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


class GitUpdateJob(Job):
    """Self-update a git checkout and restart the bot."""

    def __init__(
        self,
        branch: str,
        commit: str | None = None,
        *,
        ref_type: str = "branch",
        project_root: Path | None = None,
        restart: bool = True,
    ) -> None:
        super().__init__(kind="git_update", lock_name="git")
        self.branch = branch
        self.commit = commit
        self.ref_type = ref_type
        self.project_root = project_root or Path.cwd()
        self.restart = restart
        self._original_branch: str | None = None
        self._original_commit: str | None = None

    def _emit_stage(self, stage: str, line: str) -> None:
        self.emit({"type": "stage", "stage": stage, "line": line})

    async def _emit_git_output(self, stage: str, output: str) -> None:
        for line in output.splitlines():
            if line.strip():
                self._emit_stage(stage, line)

    async def run(self) -> None:
        rc, dirty, _ = await _run_git("status", "--porcelain", cwd=self.project_root)
        if rc == 0 and dirty:
            raise JobError(_DIRTY_BLOCK_MESSAGE)

        _, self._original_commit, _ = await _run_git(
            "rev-parse", "HEAD", cwd=self.project_root
        )
        _, original_branch, _ = await _run_git(
            "branch", "--show-current", cwd=self.project_root
        )
        self._original_branch = original_branch or None
        logger.info(
            "Starting update to {} '{}' from {} ({})",
            self.ref_type,
            self.branch,
            self._original_branch or "detached HEAD",
            (self._original_commit or "")[:7],
        )

        if self.ref_type == "tag":
            await self._run_tag_update()
        else:
            await self._run_branch_update()

        rc = await run_uv_sync(self, self.project_root)
        if rc != 0:
            msg = f"uv sync 返回码: {rc}"
            raise JobError(msg)

        self._emit_stage("done", "更新完成，即将重启...")
        logger.success(
            "Git update to {} '{}' completed. Restarting...",
            self.ref_type,
            self.branch,
        )

        if self.restart:
            from apeiria.utils.restart import graceful_restart

            await asyncio.sleep(0.8)
            await graceful_restart()

    async def _run_branch_update(self) -> None:
        self._emit_stage("checkout", f"$ git checkout {self.branch}")
        rc, out, err = await _run_git("checkout", self.branch, cwd=self.project_root)
        if rc != 0:
            rc2, _, err2 = await _run_git(
                "checkout",
                "-b",
                self.branch,
                f"origin/{self.branch}",
                cwd=self.project_root,
            )
            if rc2 != 0:
                msg = f"Checkout 失败: {err2 or err}"
                raise JobError(msg)
            out = f"Switched to a new branch '{self.branch}'"
        self.rollback_needed = True
        await self._emit_git_output("checkout", out)
        await self._emit_git_output("checkout", err)

        self._emit_stage("pull", f"$ git fetch origin {self.branch}")
        rc3, _, fetch_err = await _run_git(
            "fetch", "origin", self.branch, cwd=self.project_root
        )
        if rc3 != 0:
            msg = f"Fetch 失败: {fetch_err}"
            raise JobError(msg)

        target_ref = self.commit or f"origin/{self.branch}"
        self._emit_stage("pull", f"$ git reset --hard {target_ref}")
        rc4, reset_out, reset_err = await _run_git(
            "reset", "--hard", target_ref, cwd=self.project_root
        )
        await self._emit_git_output("pull", reset_out)
        await self._emit_git_output("pull", reset_err)
        if rc4 != 0:
            msg = f"Reset 失败: {reset_err}"
            raise JobError(msg)

    async def _run_tag_update(self) -> None:
        self._emit_stage("checkout", "$ git fetch origin --tags")
        rc_fetch, _, fetch_err = await _run_git(
            "fetch", "origin", "--tags", cwd=self.project_root
        )
        if rc_fetch != 0:
            msg = f"Fetch tags 失败: {fetch_err}"
            raise JobError(msg)

        target = self.commit or self.branch
        self._emit_stage("checkout", f"$ git checkout {target}")
        rc, out, err = await _run_git("checkout", target, cwd=self.project_root)
        if rc != 0:
            msg = f"Checkout 失败: {err}"
            raise JobError(msg)
        self.rollback_needed = True
        await self._emit_git_output("checkout", out)
        await self._emit_git_output("checkout", err)

    async def rollback(self) -> None:
        if not self.rollback_needed or not self._original_commit:
            return
        original_branch = self._original_branch
        original_commit = self._original_commit
        logger.warning(
            "Rolling back to {} ({})",
            original_branch or "detached HEAD",
            original_commit[:7],
        )
        self._emit_stage("rollback", "正在回滚到更新前状态...")

        if original_branch:
            rc, _, err = await _run_git(
                "checkout", original_branch, cwd=self.project_root
            )
            if rc != 0:
                msg = f"回滚 checkout 失败: {err}"
                raise JobError(msg)
        else:
            rc, _, err = await _run_git(
                "checkout", "--detach", original_commit, cwd=self.project_root
            )
            if rc != 0:
                msg = f"回滚 checkout 失败: {err}"
                raise JobError(msg)

        rc, _, err = await _run_git(
            "reset", "--hard", original_commit, cwd=self.project_root
        )
        if rc != 0:
            msg = f"回滚 reset 失败: {err}"
            raise JobError(msg)

        self._emit_stage("rollback", "回滚完成")
        logger.info("Rollback complete")
