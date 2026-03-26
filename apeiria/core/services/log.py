"""Logging service — file rotation + WebSocket log buffer."""

from __future__ import annotations

import asyncio
import contextlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nonebot.log import logger

from apeiria.core.i18n import t

if TYPE_CHECKING:
    from collections.abc import Mapping

    from loguru import Record


@dataclass(frozen=True)
class LogSubscription:
    """Per-connection queue used for real-time log delivery."""

    queue: asyncio.Queue["StructuredLogEntry"]
    loop: asyncio.AbstractEventLoop


@dataclass(frozen=True)
class StructuredLogEntry:
    """Structured log item used by the Web UI log stream."""

    timestamp: str
    level: str
    source: str
    message: str
    raw: str
    extra: dict[str, object]

    def to_payload(self) -> dict[str, object]:
        """Convert the log entry into a JSON-serializable payload."""
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "source": self.source,
            "message": self.message,
            "raw": self.raw,
            "extra": self.extra,
        }


class LogBuffer:
    """Circular buffer holding recent log entries for WebSocket push."""

    def __init__(self, maxlen: int = 500) -> None:
        self._buffer: deque[StructuredLogEntry] = deque(maxlen=maxlen)
        self._subscribers: list[LogSubscription] = []

    def append(self, entry: StructuredLogEntry) -> None:
        """Append a log entry and fan it out to subscribers."""
        self._buffer.append(entry)
        for subscriber in tuple(self._subscribers):
            subscriber.loop.call_soon_threadsafe(
                self._push_to_queue,
                subscriber.queue,
                entry,
            )

    def get_recent(self, n: int = 100) -> list[StructuredLogEntry]:
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
    def _push_to_queue(
        queue: asyncio.Queue[StructuredLogEntry],
        entry: StructuredLogEntry,
    ) -> None:
        if queue.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                queue.get_nowait()
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(entry)


log_buffer = LogBuffer()


def _log_format(_record: Record) -> str:
    """Custom log format for file output."""
    return (
        "[{time:YYYY-MM-DD HH:mm:ss}] [{level.name:<8}] [{name}] {message}\n{exception}"
    )


def _serialize_extra(extra: "Mapping[str, Any]") -> dict[str, object]:
    """Serialize record extras into JSON-safe primitive values."""
    serialized: dict[str, object] = {}
    for key, value in extra.items():
        if key.startswith("_"):
            continue
        if isinstance(value, str | int | float | bool) or value is None:
            serialized[key] = value
            continue
        serialized[key] = str(value)
    return serialized


def _build_log_entry(message: Any) -> StructuredLogEntry:
    """Build a structured log entry from a loguru message object."""
    record = message.record
    return StructuredLogEntry(
        timestamp=record["time"].strftime("%Y-%m-%d %H:%M:%S"),
        level=record["level"].name,
        source=str(record["name"]),
        message=str(record["message"]),
        raw=str(message).rstrip(),
        extra=_serialize_extra(record["extra"]),
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
    def _buffer_sink(message: Any) -> None:
        log_buffer.append(_build_log_entry(message))

    logger.add(
        _buffer_sink,
        format=_log_format,
        level="INFO",
    )

    logger.info("{}", t("logging.initialized", log_dir=log_dir))
