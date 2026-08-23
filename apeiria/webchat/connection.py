"""Manage active WebSocket connections for the WebChat adapter."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol
from uuid import uuid4

from nonebot.log import logger


class SupportsSendText(Protocol):
    """Protocol for objects that can send a raw text frame over a connection."""

    async def send_text(self, data: str) -> None:
        """Send a raw text frame over the connection.

        Args:
            data: The raw text to send.
        """
        ...


class ConnectionManager:
    """Manage active WebSocket connections: register, unregister, route, and broadcast.

    Connection accounting is guarded by a lock so the adapter can detect the
    first/last connection to trigger the bot going online/offline.
    """

    def __init__(self) -> None:
        """Initialize the connection registry and its accounting lock."""
        self._conns: dict[str, SupportsSendText] = {}
        self._lock = asyncio.Lock()

    async def add(self, ws: SupportsSendText) -> tuple[str, bool]:
        """Register a connection and report whether it is the first connection.

        Args:
            ws: The connection to register.

        Returns:
            A tuple of (connection_id, is_first_connection).
        """
        async with self._lock:
            is_first = len(self._conns) == 0
            conn_id = uuid4().hex
            self._conns[conn_id] = ws
            return conn_id, is_first

    async def remove(self, conn_id: str) -> bool:
        """Unregister a connection and report whether no active connection remains.

        Args:
            conn_id: The connection id to unregister.

        Returns:
            Whether the registry is now empty (this was the last connection).
        """
        async with self._lock:
            self._conns.pop(conn_id, None)
            return len(self._conns) == 0

    def count(self) -> int:
        """Return the number of active connections."""
        return len(self._conns)

    async def send_to(self, conn_id: str, frame: dict[str, Any]) -> None:
        """Send a frame to a single connection if it is active.

        Args:
            conn_id: The target connection id.
            frame: The frame to send, serialized as JSON.
        """
        ws = self._conns.get(conn_id)
        if ws is not None:
            await self._safe_send(conn_id, ws, frame)

    async def broadcast(self, frame: dict[str, Any]) -> None:
        """Send a frame to every active connection.

        Args:
            frame: The frame to broadcast, serialized as JSON.
        """
        for conn_id, ws in list(self._conns.items()):
            await self._safe_send(conn_id, ws, frame)

    async def _safe_send(
        self, conn_id: str, ws: SupportsSendText, frame: dict[str, Any]
    ) -> None:
        """Serialize and send a frame, logging but swallowing any send failure.

        Args:
            conn_id: The target connection id.
            ws: The connection to send to.
            frame: The frame to send, serialized as JSON.
        """
        try:
            await ws.send_text(json.dumps(frame, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            logger.opt(exception=True).debug(
                "webchat: failed to send to connection {}", conn_id
            )
