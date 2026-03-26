"""Logging service — file rotation + WebSocket log buffer."""

from __future__ import annotations

import asyncio
import contextlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nonebot.log import logger

from apeiria.core.i18n import t

if TYPE_CHECKING:
    from loguru import Record


@dataclass(frozen=True)
class LogSubscription:
    """Per-connection queue used for real-time log delivery."""

    queue: asyncio.Queue[str]
    loop: asyncio.AbstractEventLoop


class LogBuffer:
    """Circular buffer holding recent log entries for WebSocket push."""

    def __init__(self, maxlen: int = 500) -> None:
        self._buffer: deque[str] = deque(maxlen=maxlen)
        self._subscribers: list[LogSubscription] = []

    def append(self, message: str) -> None:
        self._buffer.append(message)
        for subscriber in tuple(self._subscribers):
            subscriber.loop.call_soon_threadsafe(
                self._push_to_queue,
                subscriber.queue,
                message,
            )

    def get_recent(self, n: int = 100) -> list[str]:
        """Get the N most recent log entries."""
        items = list(self._buffer)
        return items[-n:]

    def subscribe(self, max_queue_size: int = 200) -> LogSubscription:
        subscription = LogSubscription(
            queue=asyncio.Queue(maxsize=max_queue_size),
            loop=asyncio.get_running_loop(),
        )
        self._subscribers.append(subscription)
        return subscription

    def unsubscribe(self, subscription: LogSubscription) -> None:
        with contextlib.suppress(ValueError):
            self._subscribers.remove(subscription)

    @staticmethod
    def _push_to_queue(queue: asyncio.Queue[str], message: str) -> None:
        if queue.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                queue.get_nowait()
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(message)


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

    logger.info("{}", t("logging.initialized", log_dir=log_dir))
