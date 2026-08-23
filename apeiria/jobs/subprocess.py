"""Run subprocesses while streaming their output and supporting cancellation."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from collections.abc import Callable, Sequence
from pathlib import Path

from nonebot.log import logger


class SubprocessExecutor:
    """Run subprocesses while streaming output and supporting cancellation."""

    def __init__(self) -> None:
        """Initialize the executor with no active subprocess."""
        self._proc: asyncio.subprocess.Process | None = None

    async def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path | str | None = None,
        env: dict[str, str] | None = None,
        emit: Callable[[str], None] | None = None,
    ) -> int:
        """Run a command, streaming merged output lines to the emitter.

        Args:
            command: The command and its arguments to execute.
            cwd: Working directory for the subprocess.
            env: Environment variables to pass to the subprocess.
            emit: Optional callback invoked with each non-empty output line.

        Returns:
            The subprocess exit code, defaulting to 0 when it is None.

        Raises:
            ValueError: When the command sequence is empty.
        """
        if not command:
            msg = "subprocess command must not be empty"
            raise ValueError(msg)

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            start_new_session=os.name != "nt",
        )
        self._proc = proc
        try:
            if proc.stdout is not None:
                async for raw in proc.stdout:
                    line = raw.decode(errors="replace").rstrip()
                    if line and emit is not None:
                        emit(line)
            await proc.wait()
            return proc.returncode or 0
        finally:
            if self._proc is proc:
                self._proc = None
            if proc.returncode is None:
                logger.warning("Killing subprocess group after abnormal exit")
                self._kill(proc)

    def terminate(self) -> None:
        """Terminate the active subprocess group if one is still running."""
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        logger.info("Terminating subprocess group pid={}", proc.pid)
        if os.name != "nt":
            with contextlib.suppress(OSError, ProcessLookupError):
                os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.terminate()

    @staticmethod
    def _kill(proc: asyncio.subprocess.Process) -> None:
        """Forcefully kill a subprocess group.

        Args:
            proc: The subprocess process to kill.
        """
        if os.name != "nt":
            with contextlib.suppress(OSError, ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
