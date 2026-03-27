"""Web UI chat routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from fastapi.responses import FileResponse, RedirectResponse

from apeiria.core.i18n import t
from apeiria.domains.chat import (
    ChatAssetFileMissingError,
    ChatAssetNotFoundError,
    chat_gateway_service,
)
from apeiria.plugins.web_ui.auth import require_control_panel, verify_token
from apeiria.plugins.web_ui.roles import can_access_control_panel

router = APIRouter()


@router.get("/assets/{asset_id}", response_model=None)
async def get_chat_asset(
    asset_id: str,
    _: Annotated[Any, Depends(require_control_panel)],
) -> FileResponse | RedirectResponse:
    try:
        asset = chat_gateway_service.get_asset(asset_id)
    except ChatAssetNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.chat.asset_not_found"),
        ) from None
    except ChatAssetFileMissingError:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.chat.asset_file_missing"),
        ) from None

    if asset.remote_url:
        return RedirectResponse(asset.remote_url)
    if asset.local_path is None:
        raise HTTPException(
            status_code=404,
            detail=t("web_ui.chat.asset_file_missing"),
        )
    return FileResponse(
        asset.local_path,
        media_type=asset.content_type,
        filename=asset.file_name,
    )


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    def _verify_admin_token(token: str) -> dict[str, object]:
        claims = verify_token(token)
        if not can_access_control_panel(claims.get("role")):
            raise HTTPException(
                status_code=403,
                detail=t("web_ui.auth.permission_denied"),
            )
        return claims

    await chat_gateway_service.serve_websocket(websocket, _verify_admin_token)
