"""Provide uv subprocess helpers used by long-running package jobs."""

from __future__ import annotations

import shutil
from pathlib import Path

from nonebot.log import logger

from apeiria.jobs.base import Job, JobError
from apeiria.jobs.subprocess import SubprocessExecutor


def find_uv() -> str | None:
    """Locate uv on PATH, falling back to the default cargo install path.

    Returns:
        The absolute path to the uv executable, or None when not found.
    """
    uv = shutil.which("uv")
    if uv is not None:
        return uv
    home = Path.home() / ".cargo" / "bin" / "uv"
    if home.exists():
        return str(home)
    return None


async def _run_uv(job: Job, args: list[str], cwd: Path) -> int:
    """Run uv with the given arguments and stream its output to the job.

    Args:
        job: The job that owns the subprocess and receives output events.
        args: The arguments to pass to uv.
        cwd: Working directory for the uv command.

    Returns:
        The uv process exit code.

    Raises:
        JobError: When the uv executable cannot be found.
    """
    uv = find_uv()
    if uv is None:
        msg = "系统中未找到 uv 命令"
        raise JobError(msg)

    command = [uv, *args]
    executor = SubprocessExecutor()
    job.attach_executor(executor)
    try:
        return await executor.run(
            command,
            cwd=cwd,
            emit=lambda line: job.emit({"type": "output", "text": line}),
        )
    finally:
        job.detach_executor()


async def run_uv_add(
    job: Job,
    requirement: str,
    cwd: Path,
) -> int:
    """Add a dependency requirement to the environment via uv add.

    Args:
        job: The job that owns the subprocess and receives output events.
        requirement: The package requirement string to add.
        cwd: Working directory for the uv command.

    Returns:
        The uv process exit code.
    """
    job.emit({"type": "output", "text": f"> uv add {requirement}"})
    return await _run_uv(job, ["add", requirement], cwd)


async def run_uv_remove(
    job: Job,
    requirement: str,
    cwd: Path,
) -> int:
    """Remove a dependency requirement from the environment via uv remove.

    Args:
        job: The job that owns the subprocess and receives output events.
        requirement: The package requirement string to remove.
        cwd: Working directory for the uv command.

    Returns:
        The uv process exit code.
    """
    job.emit({"type": "output", "text": f"> uv remove {requirement}"})
    return await _run_uv(job, ["remove", requirement], cwd)


async def run_uv_sync(job: Job, cwd: Path) -> int:
    """Sync the environment dependencies via uv sync.

    Args:
        job: The job that owns the subprocess and receives output events.
        cwd: Working directory for the uv command.

    Returns:
        The uv process exit code.
    """
    job.emit({"type": "output", "text": "> uv sync"})
    return await _run_uv(job, ["sync"], cwd)


def sync_apeiria_env_sync() -> bool:
    """Synchronous helper used during bootstrap before the event loop is busy.

    Returns:
        True when the environment sync succeeds, False otherwise.
    """
    import subprocess

    uv = find_uv()
    if uv is None:
        logger.error("uv not found — install uv first: https://docs.astral.sh/uv/")
        return False

    result = subprocess.run(
        [uv, "sync", "--directory", ".apeiria"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        logger.error(
            "uv sync failed: {}", result.stderr.strip() or result.stdout.strip()
        )
        return False
    logger.success("Plugin environment synced")
    return True
