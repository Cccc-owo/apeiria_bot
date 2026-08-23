"""Web log streaming, file sinks, and history endpoints for the Web API."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from nonebot.log import logger

from apeiria.web.auth import verify_token

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from loguru import Message

    from apeiria.config.models import LogConfig

_DEFAULT_BUFFER = 500
_LEVEL_NO = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}
_HEARTBEAT = 15.0

_MUTED_ACCESS_PREFIXES = ("/assets/",)
_MUTED_ACCESS_PATHS = frozenset({"/favicon.svg", "/icons.svg", "/api/status"})
_ACCESS_ARG_COUNT = 5
_ACCESS_PATH_INDEX = 2
_ACCESS_STATUS_INDEX = 4
_HTTP_ERROR = 400
_ACCESS_LOG_MAX_BYTES = 10 * 1024 * 1024
_ACCESS_LOG_BACKUPS = 5


class _StaticAccessFilter(logging.Filter):
    """Filter out successful static-asset access log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True when the access log record should be kept."""
        args = record.args
        if not isinstance(args, tuple) or len(args) < _ACCESS_ARG_COUNT:
            return True
        path = args[_ACCESS_PATH_INDEX]
        status = args[_ACCESS_STATUS_INDEX]
        is_muted = isinstance(path, str) and (
            path.startswith(_MUTED_ACCESS_PREFIXES) or path in _MUTED_ACCESS_PATHS
        )
        is_success = isinstance(status, int) and status < _HTTP_ERROR
        return not (is_muted and is_success)


def route_access_logs(cfg: LogConfig) -> None:
    """Route uvicorn access logs to a dedicated file, off the console and SSE.

    Args:
        cfg: Log configuration providing the log file location.
    """
    from nonebot import get_driver

    path = Path(cfg.file).parent / "access.log"

    def _apply() -> None:
        """Configure the uvicorn access logger to write to a rotating file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        access = logging.getLogger("uvicorn.access")
        for handler in list(access.handlers):
            access.removeHandler(handler)
        access.propagate = False
        file_handler = RotatingFileHandler(
            str(path),
            maxBytes=_ACCESS_LOG_MAX_BYTES,
            backupCount=_ACCESS_LOG_BACKUPS,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s"),
        )
        file_handler.addFilter(_StaticAccessFilter())
        access.addHandler(file_handler)

    get_driver().on_startup(_apply)


class _AsgiCancelledFilter(logging.Filter):
    """Filter out log records raised by a CancelledError."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True when the record is not raised by a CancelledError."""
        exc = record.exc_info[1] if record.exc_info else None
        return not isinstance(exc, asyncio.CancelledError)


def quiet_asgi_cancel_errors() -> None:
    """Silence benign CancelledError ASGI-app error logs.

    Examples include the log SSE stream force-cancelled by uvicorn's
    graceful-shutdown timeout.
    """
    from nonebot import get_driver

    def _apply() -> None:
        """Attach the CancelledError filter to the uvicorn error logger."""
        logging.getLogger("uvicorn.error").addFilter(_AsgiCancelledFilter())

    get_driver().on_startup(_apply)


def _parse_log_line(line: str) -> dict[str, Any] | None:
    """Parse a serialized log line into a dictionary of its fields.

    Args:
        line: A JSON-serialized log line.

    Returns:
        A dictionary of log fields, or None when the line is not valid JSON.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    record = obj.get("record", {})
    level_obj = record.get("level", {})
    return {
        "ts": record.get("time", {}).get("timestamp"),
        "no": level_obj.get("no", 0),
        "level": level_obj.get("name", ""),
        "name": record.get("name") or "",
        "message": record.get("message") or "",
    }


def _record_matches(  # noqa: PLR0913
    record: dict[str, Any],
    *,
    level: str,
    query: str,
    source: str,
    since: float | None,
    until: float | None,
) -> bool:
    """Return True when a parsed record matches the given filters.

    Args:
        record: Parsed record dictionary.
        level: Minimum level name to keep, or empty for no filter.
        query: Text to search in message and name, or empty for no filter.
        source: Source name substring to keep, or empty for no filter.
        since: Earliest timestamp to keep, or None.
        until: Latest timestamp to keep, or None.

    Returns:
        True when the record matches all the filters; False otherwise.
    """
    if level:
        min_no = _LEVEL_NO.get(level, 0)
        if record["no"] < min_no:
            return False
    if query:
        needle = query.lower()
        if (
            needle not in record["message"].lower()
            and needle not in record["name"].lower()
        ):
            return False
    if source and source.lower() not in record["name"].lower():
        return False
    if since is not None and (record["ts"] is None or record["ts"] < since):
        return False
    return not (until is not None and (record["ts"] is None or record["ts"] > until))


def _iter_reverse_lines(path: Path) -> Iterator[str]:
    """Yield decoded lines from a log file in reverse order.

    Args:
        path: Log file path to read.

    Yields:
        Each non-empty decoded line, from the last line to the first.
    """
    with path.open("rb") as f:
        f.seek(0, 2)
        pos = f.tell()
        pending = b""
        while pos > 0:
            read_size = min(64 * 1024, pos)
            pos -= read_size
            f.seek(pos)
            chunk = f.read(read_size)
            data = chunk + pending
            lines = data.split(b"\n")
            pending = lines[0]
            for line in reversed(lines[1:]):
                if line:
                    yield line.decode(errors="replace")
        if pending:
            yield pending.decode(errors="replace")


class LogHub:
    """Central hub that manages log sinks and live log subscriptions."""

    def __init__(self) -> None:
        """Initialize the hub with no installed sinks or subscribers."""
        self._installed = False
        self._cfg: LogConfig | None = None
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def install_sinks(self, cfg: LogConfig) -> None:
        """Install file and broadcast log sinks for a config.

        Args:
            cfg: Log configuration to apply.
        """
        if self._installed:
            return
        self._cfg = cfg
        Path(cfg.file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            cfg.file,
            level=cfg.level,
            rotation=cfg.rotation,
            retention=cfg.retention,
            encoding="utf-8",
            enqueue=True,
            serialize=True,
        )
        logger.add(self._broadcast_sink, level=cfg.level, enqueue=True)
        self._installed = True

    def _broadcast_sink(self, message: Message) -> None:
        """Serialize a log message and fan it out to subscribers on the loop."""
        if self._loop is None or not self._subscribers:
            return
        record = message.record
        payload = json.dumps(
            {
                "ts": record["time"].timestamp(),
                "level": record["level"].name,
                "name": record["name"],
                "message": record["message"],
            },
            ensure_ascii=False,
        )
        with contextlib.suppress(RuntimeError):
            self._loop.call_soon_threadsafe(self._fanout, payload)

    def _fanout(self, payload: str) -> None:
        """Deliver a payload to all subscribers, dropping the oldest when full.

        Args:
            payload: Serialized log payload to broadcast.
        """
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(payload)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    continue

    def subscribe(self) -> asyncio.Queue[str]:
        """Create and register a subscriber queue.

        Returns:
            A new queue that receives broadcast log payloads.
        """
        buffer = self._cfg.stream_buffer if self._cfg else _DEFAULT_BUFFER
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=buffer)
        self._loop = asyncio.get_running_loop()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        """Remove a subscriber queue from the hub.

        Args:
            queue: Queue to remove.
        """
        self._subscribers.discard(queue)

    async def event_stream(self, request: Request) -> AsyncIterator[str]:
        """Yield SSE payloads to a subscriber until the client disconnects.

        Args:
            request: Streaming request to monitor for disconnection.

        Yields:
            SSE-formatted log payloads, including periodic heartbeat pings.
        """
        queue = self.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT)
                except TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"data: {payload}\n\n"
        finally:
            self.unsubscribe(queue)

    def read_history(  # noqa: PLR0913, PLR0917
        self,
        level: str = "",
        query: str = "",
        source: str = "",
        since: float | None = None,
        until: float | None = None,
        page: int = 1,
        size: int = 100,
    ) -> dict[str, Any]:
        """Read and filter recent log history from the log file.

        Args:
            level: Minimum level name to keep, or empty.
            query: Text to search in message and name, or empty.
            source: Source name substring to keep, or empty.
            since: Earliest timestamp to keep, or None.
            until: Latest timestamp to keep, or None.
            page: Page number to return.
            size: Number of items per page.

        Returns:
            A dictionary with the matching items, total count, page, and size.
        """
        path = Path(self._cfg.file) if self._cfg else None
        if path is None or not path.exists():
            return {"items": [], "total": 0, "page": page, "size": size}

        start = max((page - 1) * size, 0)
        end = start + size
        total = 0
        items: list[dict[str, Any]] = []

        for line in _iter_reverse_lines(path):
            record = _parse_log_line(line)
            if record is None or not _record_matches(
                record,
                level=level,
                query=query,
                source=source,
                since=since,
                until=until,
            ):
                continue
            if start <= total < end:
                items.append(
                    {
                        "ts": record["ts"],
                        "level": record["level"],
                        "name": record["name"],
                        "message": record["message"],
                    }
                )
            total += 1

        return {"items": items, "total": total, "page": page, "size": size}


_hub = LogHub()


def get_log_hub() -> LogHub:
    """Return the global log hub instance."""
    return _hub


logs_router = APIRouter(prefix="/api/logs", tags=["logs"])


@logs_router.get("/stream", dependencies=[Depends(verify_token)])
async def stream(request: Request) -> StreamingResponse:
    """Stream recent history and live log events to the client as SSE.

    Args:
        request: The streaming request.

    Returns:
        A server-sent events stream response.
    """
    hub = get_log_hub()

    async def event_stream_with_history() -> AsyncIterator[str]:
        """Yield recent history followed by live log events as SSE payloads."""
        history = await asyncio.to_thread(hub.read_history, page=1, size=50)
        for record in reversed(history["items"]):
            yield f"data: {json.dumps(record, ensure_ascii=False)}\n\n"

        async for event in hub.event_stream(request):
            yield event

    return StreamingResponse(
        event_stream_with_history(),
        media_type="text/event-stream",
    )


@logs_router.get("/history", dependencies=[Depends(verify_token)])
async def history(  # noqa: PLR0913, PLR0917
    level: str = "",
    q: str = "",
    source: str = "",
    since: float | None = None,
    until: float | None = None,
    page: int = 1,
    size: int = 100,
) -> JSONResponse:
    """Return matching log history as a JSON response.

    Args:
        level: Minimum level name to keep, or empty.
        q: Text to search in message and name, or empty.
        source: Source name substring to keep, or empty.
        since: Earliest timestamp to keep, or None.
        until: Latest timestamp to keep, or None.
        page: Page number to return.
        size: Number of items per page.

    Returns:
        A JSON response with the matching log history.
    """
    result = await asyncio.to_thread(
        get_log_hub().read_history,
        level,
        q,
        source,
        since,
        until,
        page,
        size,
    )
    return JSONResponse(content=result)
