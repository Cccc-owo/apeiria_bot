"""Cache service — abstract backend with in-memory default."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any


class CacheBackend(ABC):
    """Abstract cache interface. Swap implementations via config."""

    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def clear(self) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...


class MemoryCache(CacheBackend):
    """In-memory dict cache with TTL support."""

    def __init__(self) -> None:
        # key -> (value, expiry_timestamp | None)
        self._store: dict[str, tuple[Any, float | None]] = {}

    def _is_expired(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return True
        _, expiry = entry
        if expiry is not None and time.monotonic() > expiry:
            del self._store[key]
            return True
        return False

    async def get(self, key: str) -> Any | None:
        if self._is_expired(key):
            return None
        entry = self._store.get(key)
        return entry[0] if entry else None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = (time.monotonic() + ttl) if ttl else None
        self._store[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()

    async def exists(self, key: str) -> bool:
        return not self._is_expired(key)


_cache: CacheBackend | None = None


def get_cache() -> CacheBackend:
    """Get the global cache singleton."""
    global _cache  # noqa: PLW0603
    if _cache is None:
        _cache = MemoryCache()
    return _cache
