"""Web UI chat routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import ValidationError

from apeiria.core.i18n import t
from apeiria.core.services.web_chat import WebChatConnection, web_chat_service
from apeiria.core.services.web_chat.protocol import (
    AuthHelloPayload,
    ChatEnvelope,
    MessageSendPayload,
    SessionCreatePayload,
    SessionDeletePayload,
    SessionUpdatePayload,
)
from apeiria.plugins.web_ui.auth import verify_token

router = APIRouter()


@router.get("/assets/{asset_id}", response_model=None)
async def get_chat_asset(
    asset_id: str,
    token: str = Query(...),  # noqa: FAST002
) -> FileResponse | RedirectResponse:
    verify_token(token)

    asset = web_chat_service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=t("web_ui.chat.asset_not_found"))

    if asset.remote_url:
        return RedirectResponse(asset.remote_url)
    if asset.local_path and asset.local_path.is_file():
        return FileResponse(
            asset.local_path,
            media_type=asset.content_type,
            filename=asset.file_name,
        )
    raise HTTPException(status_code=404, detail=t("web_ui.chat.asset_file_missing"))


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket) -> None:  # noqa: C901, PLR0912, PLR0915
    await websocket.accept()
    connection = WebChatConnection(websocket)
    active_session_id: str | None = None

    try:
        while True:
            frame = ChatEnvelope.model_validate(await websocket.receive_json())
            if frame.type != "auth.hello" and connection.principal is None:
                await web_chat_service.emit_error(
                    connection,
                    code="AUTH_REQUIRED",
                    message=t("web_ui.chat.auth_required"),
                    request_id=frame.request_id,
                )
                continue

            match frame.type:
                case "auth.hello":
                    try:
                        payload = AuthHelloPayload.model_validate(frame.payload)
                        claims = verify_token(payload.token)
                        principal = web_chat_service.build_principal(claims)
                        await web_chat_service.emit_auth_ok(
                            connection,
                            principal,
                            request_id=frame.request_id,
                        )
                        await web_chat_service.emit_system_info(
                            connection,
                            t("web_ui.chat.auth_connected"),
                        )
                        await web_chat_service.emit_session_list(
                            connection,
                            principal,
                        )
                    except HTTPException as e:
                        await web_chat_service.emit_error(
                            connection,
                            code="AUTH_FAILED",
                            message=str(e.detail),
                            request_id=frame.request_id,
                            type_="auth.error",
                        )
                case "capabilities.request":
                    await web_chat_service.emit_capabilities(
                        connection,
                        request_id=frame.request_id,
                    )
                case "session.create":
                    payload = SessionCreatePayload.model_validate(frame.payload)
                    session = web_chat_service.create_session(
                        connection.principal,
                        payload,
                    )
                    active_session_id = session.session_id
                    await web_chat_service.emit_session_state(
                        connection,
                        session,
                        request_id=frame.request_id,
                    )
                    await web_chat_service.emit_session_list(
                        connection,
                        connection.principal,
                    )
                case "session.update":
                    payload = SessionUpdatePayload.model_validate(frame.payload)
                    session = web_chat_service.update_session(
                        connection.principal,
                        payload,
                    )
                    active_session_id = session.session_id
                    await web_chat_service.emit_session_state(
                        connection,
                        session,
                        request_id=frame.request_id,
                    )
                    await web_chat_service.emit_session_list(
                        connection,
                        connection.principal,
                    )
                case "message.send":
                    payload = MessageSendPayload.model_validate(frame.payload)
                    await web_chat_service.handle_message(connection, payload)
                    await web_chat_service.emit_session_list(
                        connection,
                        connection.principal,
                    )
                case "session.list":
                    await web_chat_service.emit_session_list(
                        connection,
                        connection.principal,
                        request_id=frame.request_id,
                    )
                case "session.close":
                    if active_session_id:
                        web_chat_service.close_session(active_session_id)
                        await web_chat_service.emit_system_info(
                            connection,
                            t("web_ui.chat.session_closed"),
                        )
                        await web_chat_service.emit_session_list(
                            connection,
                            connection.principal,
                        )
                        active_session_id = None
                case "session.clear_history":
                    if active_session_id and connection.principal is not None:
                        session = web_chat_service.clear_history(
                            active_session_id,
                            connection.principal,
                        )
                        await web_chat_service.emit_session_state(
                            connection,
                            session,
                            request_id=frame.request_id,
                            type_="session.history_cleared",
                        )
                        await web_chat_service.emit_session_list(
                            connection,
                            connection.principal,
                        )
                case "session.delete":
                    if connection.principal is not None:
                        payload = SessionDeletePayload.model_validate(frame.payload)
                        deleted_session_id = web_chat_service.delete_session(
                            connection.principal,
                            payload,
                        )
                        if active_session_id == deleted_session_id:
                            active_session_id = None
                        await web_chat_service.emit_session_deleted(
                            connection,
                            deleted_session_id,
                            request_id=frame.request_id,
                        )
                        await web_chat_service.emit_session_list(
                            connection,
                            connection.principal,
                        )
                case _:
                    await web_chat_service.emit_error(
                        connection,
                        code="UNSUPPORTED_FRAME",
                        message=t("web_ui.chat.unsupported_frame", type=frame.type),
                        request_id=frame.request_id,
                    )
    except ValidationError as e:
        await web_chat_service.emit_error(
            connection,
            code="INVALID_FRAME",
            message=f"{t('web_ui.chat.invalid_frame')}: {e}",
            type_="system.error",
        )
    except WebSocketDisconnect:
        if active_session_id:
            web_chat_service.close_session(active_session_id)
    except Exception as e:  # noqa: BLE001
        await web_chat_service.emit_error(
            connection,
            code="INTERNAL_ERROR",
            message=f"{t('web_ui.chat.internal_error')}: {e}",
            type_="system.error",
        )
        await websocket.close(code=1011, reason=t("web_ui.chat.websocket_close_reason"))
