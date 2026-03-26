"""Service and gateway for WebChat."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import HTTPException, status
from nonebot.log import logger
from nonebot.message import handle_event

from apeiria.core.i18n import t

from .adapter import WebChatAdapter
from .assets import AssetManager, ChatAsset
from .bot import WebChatBot
from .codec import MessageCodec
from .event import WebChatMessageEvent
from .protocol import (
    AuthOkPayload,
    CapabilitiesResponsePayload,
    ChatCapabilities,
    ChatSessionState,
    ErrorPayload,
    ImageSegment,
    MentionSegment,
    MessageAckPayload,
    MessageReceivePayload,
    MessageSendPayload,
    ReplySegment,
    SessionCreatePayload,
    SessionDeletedPayload,
    SessionDeletePayload,
    SessionListItem,
    SessionListPayload,
    SessionStatePayload,
    SessionStatus,
    SessionUpdatePayload,
    SystemMessagePayload,
    TextSegment,
    WebUIPrincipal,
)
from .session import ChatSession
from .store import WebChatStore

if TYPE_CHECKING:
    from .connection import WebChatConnection


class WebChatService:
    def __init__(self) -> None:
        self.store = WebChatStore()
        self._sessions, self._history = self.store.load()
        self.assets = AssetManager()
        self.codec = MessageCodec(self.assets)
        self._adapter: WebChatAdapter | None = None

    def get_capabilities(self) -> ChatCapabilities:
        return ChatCapabilities(
            segment_types=["text", "image", "mention", "reply", "raw"],
            mock_apis=[],
        )

    def build_principal(self, claims: dict[str, Any]) -> WebUIPrincipal:
        username = str(claims.get("username") or claims.get("sub") or "webui")
        return WebUIPrincipal(
            id=str(claims.get("user_id") or claims.get("sub") or "webui_admin"),
            username=username,
            role=str(claims.get("role") or "admin"),
        )

    def create_session(
        self,
        principal: WebUIPrincipal,
        payload: SessionCreatePayload,
    ) -> ChatSessionState:
        if session := self._find_session(principal.id, payload.target_user_id):
            session.status = SessionStatus.READY
            session.updated_at = datetime.now(UTC)
            self._persist()
            return session.to_state()

        session = ChatSession.create(
            session_id=f"sess_{uuid4().hex}",
            created_by=principal,
            target_user_id=payload.target_user_id,
        )
        self._sessions[session.session_id] = session
        self._history[session.session_id] = []
        self._persist()
        return session.to_state()

    def update_session(
        self,
        principal: WebUIPrincipal,
        payload: SessionUpdatePayload,
    ) -> ChatSessionState:
        session = self._get_session(payload.session_id)
        if session.created_by.id != principal.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=t("web_ui.sessions.owner_mismatch"),
            )
        if payload.target_user_id is not None:
            resumed_session = self._find_session(
                principal.id,
                payload.target_user_id,
            )
            if resumed_session:
                resumed_session.status = SessionStatus.READY
                resumed_session.updated_at = datetime.now(UTC)
                self._persist()
                return resumed_session.to_state()
            session.target_user_id = payload.target_user_id
            self._history[session.session_id] = []
            self._prune_assets()
        session.updated_at = datetime.now(UTC)
        self._persist()
        return session.to_state()

    def get_asset(self, asset_id: str) -> ChatAsset | None:
        return self.assets.get(asset_id)

    def list_sessions(self, principal: WebUIPrincipal) -> list[SessionListItem]:
        sessions = [
            self._build_session_list_item(session)
            for session in self._sessions.values()
            if session.created_by.id == principal.id
        ]
        return sorted(
            sessions,
            key=lambda item: (
                item.last_message_at
                or item.session.updated_at
                or datetime.min.replace(tzinfo=UTC)
            ),
            reverse=True,
        )

    async def handle_message(
        self,
        connection: "WebChatConnection",
        payload: MessageSendPayload,
    ) -> None:
        session = self._get_session(payload.session_id)
        if not connection.principal or session.created_by.id != connection.principal.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=t("web_ui.sessions.owner_mismatch"),
            )

        await connection.send_envelope(
            "message.ack",
            MessageAckPayload(
                session_id=session.session_id,
                message_id=payload.message_id,
                accepted=True,
            ),
        )

        await self.emit_message(
            connection,
            MessageReceivePayload(
                session_id=session.session_id,
                message_id=payload.message_id,
                role="user",
                segments=payload.segments,
                timestamp=datetime.now(UTC),
            ),
        )

        logger.info(
            "[webui-chat] principal={} session={} user={} msg={}",
            session.created_by.username,
            session.session_id,
            session.target_user_id,
            self._summarize_segments(payload.segments),
        )

        bot = WebChatBot(self._get_adapter(), session, connection, self)
        event = self._build_event(session, payload.message_id, payload.segments)
        try:
            await handle_event(bot, event)
        except Exception as e:  # noqa: BLE001
            await bot.emit_error(str(e))

    async def emit_auth_ok(
        self,
        connection: "WebChatConnection",
        principal: WebUIPrincipal,
        request_id: str | None = None,
    ) -> None:
        connection.principal = principal
        await connection.send_envelope(
            "auth.ok",
            AuthOkPayload(principal=principal),
            request_id=request_id,
        )

    async def emit_capabilities(
        self,
        connection: "WebChatConnection",
        request_id: str | None = None,
    ) -> None:
        await connection.send_envelope(
            "capabilities.response",
            CapabilitiesResponsePayload(capabilities=self.get_capabilities()),
            request_id=request_id,
        )

    async def emit_session_state(
        self,
        connection: "WebChatConnection",
        session: Any,
        request_id: str | None = None,
        *,
        type_: str = "session.state",
    ) -> None:
        await connection.send_envelope(
            type_,
            SessionStatePayload(
                session=session,
                history=self._history.get(session.session_id, []),
            ),
            request_id=request_id,
        )

    async def emit_session_list(
        self,
        connection: "WebChatConnection",
        principal: WebUIPrincipal,
        request_id: str | None = None,
    ) -> None:
        await connection.send_envelope(
            "session.list",
            SessionListPayload(sessions=self.list_sessions(principal)),
            request_id=request_id,
        )

    async def emit_system_info(
        self,
        connection: "WebChatConnection",
        message: str,
    ) -> None:
        await connection.send_envelope(
            "system.info",
            SystemMessagePayload(message=message),
        )

    async def emit_message(
        self,
        connection: "WebChatConnection",
        payload: MessageReceivePayload,
    ) -> None:
        self._history.setdefault(payload.session_id, []).append(payload)
        self._history[payload.session_id] = self._history[payload.session_id][-100:]
        self._prune_assets()
        self._persist()
        await connection.send_envelope("message.receive", payload)

    async def emit_error(
        self,
        connection: "WebChatConnection",
        *,
        code: str,
        message: str,
        request_id: str | None = None,
        type_: str = "system.error",
    ) -> None:
        await connection.send_envelope(
            type_,
            ErrorPayload(code=code, message=message),
            request_id=request_id,
        )

    def close_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        session.status = SessionStatus.CLOSED
        session.updated_at = datetime.now(UTC)
        self._persist()

    def clear_history(
        self,
        session_id: str,
        principal: WebUIPrincipal,
    ) -> ChatSessionState:
        session = self._get_session(session_id)
        if session.created_by.id != principal.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=t("web_ui.sessions.owner_mismatch"),
        )
        self._history[session_id] = []
        session.updated_at = datetime.now(UTC)
        self._prune_assets()
        self._persist()
        return session.to_state()

    def delete_session(
        self,
        principal: WebUIPrincipal,
        payload: SessionDeletePayload,
    ) -> str:
        session = self._get_session(payload.session_id)
        if session.created_by.id != principal.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=t("web_ui.sessions.owner_mismatch"),
        )
        self._sessions.pop(payload.session_id, None)
        self._history.pop(payload.session_id, None)
        self._prune_assets()
        self._persist()
        return payload.session_id

    async def emit_session_deleted(
        self,
        connection: "WebChatConnection",
        session_id: str,
        request_id: str | None = None,
    ) -> None:
        await connection.send_envelope(
            "session.deleted",
            SessionDeletedPayload(session_id=session_id),
            request_id=request_id,
        )

    def _get_session(self, session_id: str) -> ChatSession:
        session = self._sessions.get(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("web_ui.sessions.not_found"),
            )
        return session

    def _get_adapter(self) -> WebChatAdapter:
        if self._adapter is None:
            import nonebot

            self._adapter = WebChatAdapter(nonebot.get_driver())
        return self._adapter

    def _find_session(
        self,
        principal_id: str,
        target_user_id: str,
    ) -> ChatSession | None:
        candidates = [
            session
            for session in self._sessions.values()
            if session.created_by.id == principal_id
            and session.target_user_id == target_user_id
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda session: session.updated_at)

    def _persist(self) -> None:
        self.store.save(self._sessions, self._history)

    def _prune_assets(self) -> None:
        self.assets.retain(self._referenced_asset_ids())

    def _referenced_asset_ids(self) -> set[str]:
        referenced: set[str] = set()
        for messages in self._history.values():
            for message in messages:
                for segment in message.segments:
                    if isinstance(segment, ImageSegment) and segment.asset_id:
                        referenced.add(segment.asset_id)
        return referenced

    def _build_session_list_item(self, session: ChatSession) -> SessionListItem:
        history = self._history.get(session.session_id, [])
        last_message = history[-1] if history else None
        return SessionListItem(
            session=session.to_state(),
            message_count=len(history),
            last_message=(
                self._summarize_segments(last_message.segments)
                if last_message
                else None
            ),
            last_message_at=last_message.timestamp if last_message else None,
        )

    def _summarize_segments(self, segments: list[Any]) -> str:
        parts: list[str] = []
        for segment in segments:
            if isinstance(segment, TextSegment):
                parts.append(segment.text)
            elif isinstance(segment, ImageSegment):
                parts.append("[image]")
            elif isinstance(segment, MentionSegment):
                parts.append(f"@{segment.display or segment.target}")
            elif isinstance(segment, ReplySegment):
                parts.append(f"[reply:{segment.message_id}]")
            else:
                parts.append(f"[{segment.segment_type}]")
        return " ".join(parts)

    def _build_event(
        self,
        session: ChatSession,
        message_id: str,
        segments: list[Any],
    ) -> WebChatMessageEvent:
        return WebChatMessageEvent(
            session=session,
            message=self.codec.decode_segments(segments),
            message_id=message_id,
            timestamp=int(datetime.now(UTC).timestamp()),
        )
