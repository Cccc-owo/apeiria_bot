"""Logging service — file rotation + WebSocket log buffer."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

from nonebot.log import logger

if TYPE_CHECKING:
    from loguru import Record


class LogBuffer:
    """Circular buffer holding recent log entries for WebSocket push."""

    def __init__(self, maxlen: int = 500) -> None:
        self._buffer: deque[str] = deque(maxlen=maxlen)
        self._subscribers: list = []  # WebSocket connections

    def append(self, message: str) -> None:
        self._buffer.append(message)

    def get_recent(self, n: int = 100) -> list[str]:
        """Get the N most recent log entries."""
        items = list(self._buffer)
        return items[-n:]

    def subscribe(self, ws: object) -> None:
        self._subscribers.append(ws)

    def unsubscribe(self, ws: object) -> None:
        import contextlib

        with contextlib.suppress(ValueError):
            self._subscribers.remove(ws)


log_buffer = LogBuffer()


def _log_format(_record: Record) -> str:
    """Custom log format for file output."""
    return (
        "[{time:YYYY-MM-DD HH:mm:ss}] [{level.name:<8}] [{name}] {message}\n{exception}"
    )


def setup_logging(
    log_dir: Path | None = None,
    rotation: str = "00:00",
    retention: str = "30 days",
) -> None:
    """Configure loguru sinks: file rotation + log buffer.

    Call this on bot startup, before loading plugins.
    """
    if log_dir is None:
        log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # File sink with daily rotation
    logger.add(
        log_dir / "{time:YYYY-MM-DD}.log",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        format=_log_format,
        level="DEBUG",
        enqueue=True,  # Thread-safe async writing
    )

    # Buffer sink for WebSocket push
    def _buffer_sink(message: str) -> None:
        log_buffer.append(str(message).rstrip())

    logger.add(
        _buffer_sink,
        format=_log_format,
        level="INFO",
    )

    logger.info("Logging service initialized, log_dir={}", log_dir)
