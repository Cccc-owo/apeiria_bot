"""Log routes — WebSocket real-time log streaming."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from apeiria.plugins.web_ui.auth import verify_token

router = APIRouter()


@router.websocket("/ws")
async def log_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time log streaming.

    Client sends JWT token as first message for auth.
    """
    await websocket.accept()

    # Auth: first message must be JWT token
    try:
        token = await websocket.receive_text()
        verify_token(token)
    except Exception:  # noqa: BLE001
        await websocket.close(code=4001, reason="Unauthorized")
        return

    from apeiria.core.services.log import log_buffer

    # Send recent logs
    for line in log_buffer.get_recent(50):
        await websocket.send_text(line)

    # Stream new logs
    import asyncio

    last_count = len(log_buffer._buffer)
    try:
        while True:
            await asyncio.sleep(0.5)
            current = list(log_buffer._buffer)
            if len(current) > last_count:
                new_lines = current[last_count:]
                for line in new_lines:
                    await websocket.send_text(line)
            last_count = len(current)
    except WebSocketDisconnect:
        pass
