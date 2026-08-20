from __future__ import annotations

import shutil
from pathlib import Path

from nonebot.log import logger

from apeiria.jobs.base import Job, JobError
from apeiria.jobs.subprocess import SubprocessExecutor


def find_uv() -> str | None:
    """Locate uv on PATH, falling back to the default cargo install path."""
    uv = shutil.which("uv")
    if uv is not None:
        return uv
    home = Path.home() / ".cargo" / "bin" / "uv"
    if home.exists():
        return str(home)
    return None


async def _run_uv(job: Job, args: list[str], cwd: Path) -> int:
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
    job.emit({"type": "output", "text": f"> uv add {requirement}"})
    return await _run_uv(job, ["add", requirement], cwd)


async def run_uv_remove(
    job: Job,
    requirement: str,
    cwd: Path,
) -> int:
    job.emit({"type": "output", "text": f"> uv remove {requirement}"})
    return await _run_uv(job, ["remove", requirement], cwd)


async def run_uv_sync(job: Job, cwd: Path) -> int:
    job.emit({"type": "output", "text": "> uv sync"})
    return await _run_uv(job, ["sync"], cwd)


def sync_apeiria_env_sync() -> bool:
    """Synchronous helper used during bootstrap before the event loop is busy."""
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
