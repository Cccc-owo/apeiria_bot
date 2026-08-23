"""Async SQLAlchemy engine management and the single-writer database gate."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from nonebot.log import logger
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_DEFAULT_DB_PATH = "data/apeiria.db"
_DEFAULT_BUSY_TIMEOUT = 5000
_SUPPORTED_DB_SCHEMES = frozenset({"sqlite", "sqlite+aiosqlite"})


class DbWriteGate:
    """Serialize all database writes through a single asyncio lock.

    SQLite does not allow concurrent writes, so this gate ensures that only
    one write transaction is active at a time while still allowing reads.
    """

    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        """Initialize the write gate with the given async session maker.

        Args:
            sessionmaker: Factory used to create new async sessions.
        """
        self._sessionmaker = sessionmaker
        self._write_lock = asyncio.Lock()

    @asynccontextmanager
    async def write(self) -> AsyncIterator[AsyncSession]:
        """Return an async context manager yielding a session in a write transaction.

        Yields:
            AsyncSession: A session opened inside a write transaction.
        """
        async with (
            self._write_lock,
            self._sessionmaker() as session,
            session.begin(),
        ):
            yield session

    @asynccontextmanager
    async def read(self) -> AsyncIterator[AsyncSession]:
        """Return an async context manager yielding a session for read-only access.

        Yields:
            AsyncSession: A session opened for reading.
        """
        async with self._sessionmaker() as session:
            yield session


class ApeiriaDatabase:
    """Manage the async engine, session factory, and write gate for the database."""

    def __init__(
        self,
        url: str | None = None,
        *,
        busy_timeout_ms: int = _DEFAULT_BUSY_TIMEOUT,
    ) -> None:
        """Initialize the database manager with an optional database URL.

        Args:
            url: Database URL; defaults to the configured SQLite path when omitted.
            busy_timeout_ms: Busy timeout in milliseconds for SQLite connections.
        """
        if url is None:
            url = f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"
        self._url = url
        self._busy_timeout_ms = busy_timeout_ms
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker | None = None
        self._gate: DbWriteGate | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Return the initialized async engine."""
        if self._engine is None:
            raise RuntimeError("Database not initialized")  # noqa: TRY003
        return self._engine

    @property
    def gate(self) -> DbWriteGate:
        """Return the write gate that serializes database writes."""
        if self._gate is None:
            raise RuntimeError("Database not initialized")  # noqa: TRY003
        return self._gate

    async def init(self) -> None:
        """Create the async engine, session factory, and write gate.

        Raises:
            ValueError: If the database URL is not a supported SQLite scheme.
        """
        url = make_url(self._url)
        if url.drivername not in _SUPPORTED_DB_SCHEMES:
            raise ValueError(  # noqa: TRY003
                f"Apeiria 当前仅支持 SQLite 数据库，收到不支持的数据库 URL: {self._url}"
            )

        db_path = Path(url.database) if url.database else None
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_async_engine(self._url, echo=False)
        self._sessionmaker = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._gate = DbWriteGate(self._sessionmaker)

        @event.listens_for(self._engine.sync_engine, "connect")
        def _on_connect(dbapi_connection, _connection_record):  # noqa: ANN001
            """Apply SQLite connection pragmas whenever a connection is opened."""
            if self._engine is None or self._engine.dialect.name != "sqlite":
                return
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        logger.info("Database initialized at {}", db_path or self._url)

    async def close(self) -> None:
        """Dispose the engine and clear the cached connection state."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            self._gate = None
            logger.info("Database connection closed")


_db: ApeiriaDatabase | None = None


def get_db() -> ApeiriaDatabase:
    """Return the global database instance.

    Raises:
        RuntimeError: If the database has not been initialized.
    """
    if _db is None:
        raise RuntimeError("Database not initialized")  # noqa: TRY003
    return _db


async def init_db(url: str | None = None) -> ApeiriaDatabase:
    """Initialize and return the global database instance.

    Args:
        url: Database URL; defaults to the configured SQLite path when omitted.

    Returns:
        The initialized global database instance.
    """
    global _db  # noqa: PLW0603
    _db = ApeiriaDatabase(url)
    await _db.init()
    return _db


async def close_db() -> None:
    """Close the global database instance if it is currently initialized."""
    global _db  # noqa: PLW0603
    if _db is not None:
        await _db.close()
        _db = None
