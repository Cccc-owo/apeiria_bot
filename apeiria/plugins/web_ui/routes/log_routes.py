"""Log routes — WebSocket real-time log streaming."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

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

    subscription = log_buffer.subscribe()
    try:
        while True:
            await websocket.send_text(await subscription.queue.get())
    except HTTPException:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        log_buffer.unsubscribe(subscription)
