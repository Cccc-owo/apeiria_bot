"""Logging service — file rotation + WebSocket log buffer."""

from __future__ import annotations

import asyncio
import contextlib
import heapq
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nonebot.log import logger

from apeiria.core.i18n import t

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

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


@dataclass(frozen=True)
class HistoryLogFilters:
    """History log query filters."""

    level: str = ""
    source: str = ""
    search: str = ""
    start: str = ""
    end: str = ""
    include_access: bool = True


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
LOG_LINE_PATTERN = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s"
    r"\[(?P<level>[^\]]+)\]\s"
    r"\[(?P<source>[^\]]+)\]\s"
    r"(?P<message>.*)$"
)
ACCESS_LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s(?P<message>.*)$"
)


def _log_format(_record: Record) -> str:
    """Custom log format for file output."""
    return (
        "[{time:YYYY-MM-DD HH:mm:ss}] [{level.name:<8}] [{name}] {message}\n{exception}"
    )


def _log_dir() -> Path:
    return Path("data/logs")


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
        log_dir = _log_dir()
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


def load_history_logs(
    *,
    before: int = 0,
    limit: int = 50,
    filters: HistoryLogFilters | None = None,
) -> tuple[list[StructuredLogEntry], bool, int]:
    """Load persisted logs from disk, newest first.

    Args:
        before: Number of newest history entries to skip.
        limit: Maximum number of history entries to return.
        filters: Optional history log query filters.

    Returns:
        A tuple of `(items, has_more)` where items are ordered newest first.
    """
    if limit <= 0:
        return [], False, 0

    log_dir = _log_dir()
    if not log_dir.exists():
        return [], False, 0

    active_filters = filters or HistoryLogFilters()
    items = _collect_history_entries(
        sorted(log_dir.glob("*.log"), reverse=True),
        filters=active_filters,
    )
    page = items[before : before + limit]
    return page, before + len(page) < len(items), len(items)


def load_history_log_sources() -> list[str]:
    """Load available history log sources."""
    log_dir = _log_dir()
    if not log_dir.exists():
        return []

    sources = {
        entry.source
        for entry in _collect_history_entries(
            sorted(log_dir.glob("*.log"), reverse=True),
            filters=HistoryLogFilters(),
        )
    }
    return sorted(sources)


def _collect_history_entries(
    paths: list[Path],
    *,
    filters: HistoryLogFilters,
) -> list[StructuredLogEntry]:
    """Collect persisted logs, filtered and ordered newest first."""
    start_ts = _normalize_filter_timestamp(filters.start)
    end_ts = _normalize_filter_timestamp(filters.end)
    normalized_level = filters.level.strip().upper()
    normalized_source = filters.source.strip().lower()
    normalized_search = filters.search.strip().lower()
    items: list[StructuredLogEntry] = []

    for path in paths:
        for entry in _iter_log_entries_reverse(path):
            if not filters.include_access and entry.source == "uvicorn.access":
                continue
            if normalized_level and entry.level.upper() != normalized_level:
                continue
            if normalized_source and normalized_source not in entry.source.lower():
                continue
            if start_ts and entry.timestamp < start_ts:
                continue
            if end_ts and entry.timestamp > end_ts:
                continue
            if normalized_search and not _matches_log_search(entry, normalized_search):
                continue
            items.append(entry)

    items.sort(key=lambda item: (item.timestamp, item.level, item.source, item.raw))
    items.reverse()
    return items


def _normalize_filter_timestamp(value: str | None) -> str:
    """Normalize user-provided time filters into persisted log format."""
    if not value:
        return ""

    candidate = value.strip()
    if not candidate:
        return ""

    if "T" in candidate:
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return candidate.replace("T", " ")
        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    return candidate


def _matches_log_search(entry: StructuredLogEntry, keyword: str) -> bool:
    """Return whether the log entry matches the free-text query."""
    haystack = " ".join(
        [
            entry.timestamp,
            entry.level,
            entry.source,
            entry.message,
            entry.raw,
            str(entry.extra),
        ]
    ).lower()
    return keyword in haystack


def _parse_log_text(text: str, *, source_hint: str = "") -> list[StructuredLogEntry]:
    """Parse a persisted log file using the configured line format."""
    if source_hint == "access.log":
        return _parse_access_log_text(text)

    entries: list[StructuredLogEntry] = []
    current: StructuredLogEntry | None = None

    for line in text.splitlines():
        match = LOG_LINE_PATTERN.match(line)
        if match:
            if current is not None:
                entries.append(current)
            current = StructuredLogEntry(
                timestamp=match.group("timestamp"),
                level=match.group("level").strip(),
                source=match.group("source").strip(),
                message=match.group("message"),
                raw=line,
                extra={},
            )
            continue

        if current is None:
            continue

        current = StructuredLogEntry(
            timestamp=current.timestamp,
            level=current.level,
            source=current.source,
            message=current.message,
            raw=f"{current.raw}\n{line}",
            extra=current.extra,
        )

    if current is not None:
        entries.append(current)
    return entries


def _parse_access_log_text(text: str) -> list[StructuredLogEntry]:
    """Parse uvicorn access logs persisted in access.log."""
    entries: list[StructuredLogEntry] = []
    for line in text.splitlines():
        match = ACCESS_LOG_PATTERN.match(line)
        if not match:
            continue
        entries.append(
            StructuredLogEntry(
                timestamp=match.group("timestamp"),
                level="INFO",
                source="uvicorn.access",
                message=match.group("message"),
                raw=line,
                extra={},
            )
        )
    return entries


def _collect_history_page(
    paths: list[Path],
    *,
    before: int,
    limit: int,
) -> tuple[list[StructuredLogEntry], bool]:
    remaining_skip = before
    remaining_take = limit
    collected: list[StructuredLogEntry] = []
    iterators = [_iter_log_entries_reverse(path) for path in paths]
    heap: list[tuple[str, int, StructuredLogEntry]] = []

    for source_index, iterator in enumerate(iterators):
        first = next(iterator, None)
        if first is None:
            continue
        heapq.heappush(
            heap,
            (_invert_timestamp(first.timestamp), source_index, first),
        )

    while heap:
        _, source_index, entry = heapq.heappop(heap)
        iterator = iterators[source_index]

        if remaining_skip > 0:
            remaining_skip -= 1
        else:
            collected.append(entry)
            remaining_take -= 1
            if remaining_take == 0:
                return collected, _advance_history_heap(heap, iterator, source_index)

        next_entry = next(iterator, None)
        if next_entry is not None:
            heapq.heappush(
                heap,
                (_invert_timestamp(next_entry.timestamp), source_index, next_entry),
            )

    return collected, False


def _advance_history_heap(
    heap: list[tuple[str, int, StructuredLogEntry]],
    iterator: "Iterator[StructuredLogEntry]",
    source_index: int,
) -> bool:
    if heap:
        return True

    next_entry = next(iterator, None)
    if next_entry is None:
        return False

    heapq.heappush(
        heap,
        (_invert_timestamp(next_entry.timestamp), source_index, next_entry),
    )
    return True


def _iter_log_entries_reverse(path: Path) -> "Iterator[StructuredLogEntry]":
    if path.name == "access.log":
        yield from _iter_access_log_entries_reverse(path)
        return
    yield from _iter_structured_log_entries_reverse(path)


def _iter_access_log_entries_reverse(path: Path) -> "Iterator[StructuredLogEntry]":
    for line in _iter_lines_reverse(path):
        match = ACCESS_LOG_PATTERN.match(line)
        if not match:
            continue
        yield StructuredLogEntry(
            timestamp=match.group("timestamp"),
            level="INFO",
            source="uvicorn.access",
            message=match.group("message"),
            raw=line,
            extra={},
        )


def _iter_structured_log_entries_reverse(path: Path) -> "Iterator[StructuredLogEntry]":
    tail_lines: list[str] = []
    for line in _iter_lines_reverse(path):
        match = LOG_LINE_PATTERN.match(line)
        if match:
            raw_lines = [line, *reversed(tail_lines)]
            yield StructuredLogEntry(
                timestamp=match.group("timestamp"),
                level=match.group("level").strip(),
                source=match.group("source").strip(),
                message=match.group("message"),
                raw="\n".join(raw_lines),
                extra={},
            )
            tail_lines.clear()
            continue
        tail_lines.append(line)


def _iter_lines_reverse(
    path: Path,
    *,
    chunk_size: int = 8192,
) -> "Iterator[str]":
    try:
        with path.open("rb") as file:
            file.seek(0, 2)
            position = file.tell()
            remainder = b""

            while position > 0:
                read_size = min(chunk_size, position)
                position -= read_size
                file.seek(position)
                chunk = file.read(read_size)
                parts = (chunk + remainder).split(b"\n")
                remainder = parts[0]
                for part in reversed(parts[1:]):
                    yield part.decode("utf-8", errors="replace")

            if remainder:
                yield remainder.decode("utf-8", errors="replace")
    except OSError:
        return


def _invert_timestamp(value: str) -> str:
    """Invert sortable timestamp text so heapq yields newest entries first."""
    return "".join(chr(255 - ord(char)) for char in value)
