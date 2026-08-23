"""Utilities for gracefully restarting the Apeiria bot process."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
import time
from pathlib import Path

from nonebot.log import logger

_TERM_GRACE_SECONDS = 2.0
_POLL_INTERVAL = 0.1


def _read_ppid(pid: int) -> int | None:
    """Read the parent PID of *pid* from the /proc stat file.

    Args:
        pid: Process ID to inspect.

    Returns:
        The parent process ID, or ``None`` when it cannot be determined.
    """
    try:
        content = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    rparen = content.rfind(")")
    if rparen == -1:
        return None
    fields = content[rparen + 2 :].split()
    if len(fields) < 2:  # noqa: PLR2004
        return None
    try:
        return int(fields[1])
    except ValueError:
        return None


def _build_proc_tree() -> dict[int, list[int]]:
    """Build a parent-to-children process tree by scanning /proc.

    Returns:
        Mapping from a parent PID to the list of its child PIDs, or an empty
        mapping when /proc is unavailable.
    """
    proc = Path("/proc")
    children: dict[int, list[int]] = {}
    if not proc.is_dir():
        return children
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        ppid = _read_ppid(pid)
        if ppid is None:
            continue
        children.setdefault(ppid, []).append(pid)
    return children


def _collect_descendants(children: dict[int, list[int]], root: int) -> list[int]:
    """Return every descendant PID of *root* in a process-tree map.

    Args:
        children: Mapping of parent PID to its child PIDs.
        root: Root PID whose descendants are collected.

    Returns:
        The descendant PIDs, excluding *root* itself.
    """
    result: list[int] = []
    seen: set[int] = set()
    queue = list(children.get(root, []))
    while queue:
        pid = queue.pop()
        if pid in seen:
            continue
        seen.add(pid)
        result.append(pid)
        queue.extend(children.get(pid, []))
    return result


def descendant_pids(root_pid: int) -> list[int]:
    """Return all descendant PIDs of *root_pid* by scanning /proc (Linux).

    Returns an empty list when /proc is unavailable or cannot be parsed; this
    function never raises.

    Args:
        root_pid: Root process ID whose descendants are collected.

    Returns:
        The descendant PIDs, or an empty list on failure.
    """
    return _collect_descendants(_build_proc_tree(), root_pid)


def _signal_pid(pid: int, sig: int) -> None:
    """Send *sig* to *pid*, suppressing any OSError.

    Args:
        pid: Target process ID.
        sig: Signal number to deliver.
    """
    with contextlib.suppress(OSError):
        os.kill(pid, sig)


def _pid_alive(pid: int) -> bool:
    """Report whether a process with *pid* still exists.

    Args:
        pid: Process ID to check.

    Returns:
        ``True`` when the process is present, ``False`` otherwise.
    """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


async def _terminate_descendants() -> None:
    """Terminate the current process's descendants (SIGTERM, grace, SIGKILL).

    This backs up browser processes before a restart. Killing a subtree
    without killing the caller is non-trivial on Windows and is not handled
    here.
    """
    if sys.platform == "win32":
        return
    pids = descendant_pids(os.getpid())
    if not pids:
        return
    logger.info("Terminating {} descendant process(es) before restart", len(pids))
    for pid in pids:
        _signal_pid(pid, signal.SIGTERM)
    deadline = time.monotonic() + _TERM_GRACE_SECONDS
    while time.monotonic() < deadline:
        if not any(_pid_alive(pid) for pid in pids):
            return
        await asyncio.sleep(_POLL_INTERVAL)
    for pid in pids:
        if _pid_alive(pid):
            _signal_pid(pid, signal.SIGKILL)


async def _shutdown_render_safe() -> None:
    """Shut down the HTML render service, ignoring any errors."""
    try:
        from nonebot_plugin_htmlrender import shutdown_render

        await shutdown_render()
    except Exception:  # noqa: BLE001
        logger.opt(exception=True).debug("shutdown_render skipped during restart")


async def _close_db_safe() -> None:
    """Close the database connection, ignoring any errors."""
    try:
        from apeiria.db.engine import close_db

        await close_db()
    except Exception:  # noqa: BLE001
        logger.opt(exception=True).debug("close_db failed during restart")


def _exec_restart() -> None:
    """Flush standard streams and replace the process image to restart the bot.

    A new process is spawned on Windows and the current one exits; on other
    platforms the interpreter is re-executed. This function does not return.
    """
    with contextlib.suppress(OSError):
        sys.stdout.flush()
        sys.stderr.flush()

    if sys.platform == "win32":
        import subprocess

        subprocess.Popen(
            [sys.executable, *sys.argv],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # type: ignore[attr-defined]
        )
        os._exit(0)
    else:
        os.execv(sys.executable, [sys.executable, *sys.argv])


async def graceful_restart() -> None:
    """Clean up resources and restart the bot gracefully.

    Shuts down the render tree, closes the database, kills any remaining
    descendants, then replaces the process image. Each step tolerates failures
    independently; the caller is responsible for notifying users before calling
    this. This function does not return.
    """
    logger.info("Graceful restart: cleaning up before re-exec")
    await _shutdown_render_safe()
    await _close_db_safe()
    await _terminate_descendants()
    _exec_restart()
