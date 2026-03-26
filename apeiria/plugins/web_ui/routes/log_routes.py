"""Log routes — history + WebSocket real-time log streaming."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from apeiria.plugins.web_ui.auth import verify_token
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import LogHistoryResponse, LogItem

router = APIRouter()


@router.get("/history", response_model=LogHistoryResponse)
async def get_log_history(
    _: Annotated[Any, Depends(require_auth)],
    before: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> LogHistoryResponse:
    from apeiria.core.services.log import load_history_logs

    items, has_more = load_history_logs(before=before, limit=limit)
    return LogHistoryResponse(
        items=[
            LogItem(
                timestamp=item.timestamp,
                level=item.level,
                source=item.source,
                message=item.message,
                raw=item.raw,
                extra=item.extra,
            )
            for item in items
        ],
        before=before,
        next_before=before + len(items) if has_more else None,
        has_more=has_more,
    )


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

    subscription = log_buffer.subscribe()
    try:
        while True:
            await websocket.send_json((await subscription.queue.get()).to_payload())
    except HTTPException:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        log_buffer.unsubscribe(subscription)
