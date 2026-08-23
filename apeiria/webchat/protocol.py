"""Wire protocol helpers and inbound frame models for the WebChat adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apeiria.webchat.message import Message, MessageSegment


class ProtocolError(ValueError):
    """Raised when an inbound frame is malformed."""


@dataclass
class InboundMessage:
    """An inbound message frame carrying text, an optional image, and an identity."""

    text: str
    image: str | None
    identity: dict[str, Any]


@dataclass
class InboundClear:
    """An inbound frame requesting that a session be cleared."""


@dataclass
class InboundDelete:
    """An inbound frame requesting deletion of a message by id."""

    message_id: str


@dataclass
class InboundSwitch:
    """An inbound frame requesting a switch to a new session identity."""

    identity: dict[str, Any]


InboundFrame = InboundMessage | InboundClear | InboundDelete | InboundSwitch


def parse_inbound(raw: Any) -> InboundFrame:
    """Parse a raw inbound frame into the matching inbound model.

    Args:
        raw: The decoded inbound frame data.

    Returns:
        The parsed inbound frame model.

    Raises:
        ProtocolError: If the frame is not an object, has an unknown type, or
            is missing required fields.
    """
    if not isinstance(raw, dict):
        raise ProtocolError("frame must be an object")  # noqa: TRY003
    ftype = raw.get("type")
    if ftype == "message":
        text = str(raw.get("text") or "")
        image = raw.get("image")
        identity = raw.get("identity") or {}
        if not isinstance(identity, dict):
            raise ProtocolError("identity must be an object")  # noqa: TRY003
        if not text and not image:
            raise ProtocolError("message requires text or image")  # noqa: TRY003
        return InboundMessage(text=text, image=image, identity=identity)
    if ftype == "clear":
        return InboundClear()
    if ftype == "delete":
        message_id = raw.get("message_id")
        if message_id is None or message_id == "":
            raise ProtocolError("delete requires message_id")  # noqa: TRY003
        return InboundDelete(message_id=str(message_id))
    if ftype == "switch":
        identity = raw.get("identity") or {}
        if not isinstance(identity, dict):
            raise ProtocolError("identity must be an object")  # noqa: TRY003
        return InboundSwitch(identity=identity)
    raise ProtocolError(f"unknown frame type: {ftype!r}")  # noqa: TRY003


def build_inbound_message(text: str, image: str | None) -> Message:
    """Assemble inbound text and an optional image into a WebChat message.

    Args:
        text: The inbound text content.
        image: The inbound image as a URL or a base64 data string.

    Returns:
        A WebChat message containing the text and/or image segments.
    """
    msg = Message()
    if text:
        msg.append(MessageSegment.text(text))
    if image:
        if image.startswith(("http://", "https://")):
            msg.append(MessageSegment.image(url=image))
        else:
            msg.append(MessageSegment.image(base64=image))
    if not msg:
        msg.append(MessageSegment.text(""))
    return msg


def message_to_wire(message: Message) -> list[dict[str, Any]]:
    """Serialize an outbound message into wire segments, degrading unknown types.

    Args:
        message: The message to serialize.

    Returns:
        A list of wire-format segment dictionaries.
    """
    wire: list[dict[str, Any]] = []
    for seg in message:
        if seg.type == "text":
            wire.append({"type": "text", "text": seg.data.get("text", "")})
        elif seg.type == "image":
            url = seg.data.get("url") or seg.data.get("base64") or ""
            wire.append({"type": "image", "url": url})
        elif seg.type == "raw":
            wire.append(
                {
                    "type": "raw",
                    "seg_type": seg.data.get("seg_type", "raw"),
                    "data": seg.data.get("data", {}),
                }
            )
        else:
            wire.append({"type": "raw", "seg_type": seg.type, "data": dict(seg.data)})
    return wire


def wire_message(  # noqa: PLR0913
    *,
    message_id: str,
    role: str,
    segments: list[dict[str, Any]],
    time: str,
    session_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Build a wire-format message object.

    Args:
        message_id: The id of the message.
        role: The sender role (user or bot).
        segments: The wire-format message segments.
        time: The message timestamp.
        session_id: The session the message belongs to.
        user_id: The id of the user who sent the message.

    Returns:
        A wire-format message dictionary.
    """
    return {
        "id": message_id,
        "role": role,
        "segments": segments,
        "time": time,
        "session_id": session_id,
        "user_id": user_id,
    }


def message_frame(wire_msg: dict[str, Any]) -> dict[str, Any]:
    """Wrap a wire message in a message frame.

    Args:
        wire_msg: The wire-format message.

    Returns:
        A message frame dictionary.
    """
    return {"type": "message", "message": wire_msg}


def history_frame(messages: list[dict[str, Any]], session_id: str) -> dict[str, Any]:
    """Build a history frame carrying a session's messages.

    Args:
        messages: The wire-format messages to replay.
        session_id: The session the messages belong to.

    Returns:
        A history frame dictionary.
    """
    return {"type": "history", "session_id": session_id, "messages": messages}


def cleared_frame(session_id: str) -> dict[str, Any]:
    """Build a frame notifying that a session was cleared.

    Args:
        session_id: The session that was cleared.

    Returns:
        A cleared frame dictionary.
    """
    return {"type": "cleared", "session_id": session_id}


def deleted_frame(message_id: str) -> dict[str, Any]:
    """Build a frame notifying that a message was deleted.

    Args:
        message_id: The id of the deleted message.

    Returns:
        A deleted frame dictionary.
    """
    return {"type": "deleted", "message_id": message_id}


def error_frame(code: str, message: str) -> dict[str, Any]:
    """Build an error frame with a code and a message.

    Args:
        code: The error code.
        message: The human-readable error message.

    Returns:
        An error frame dictionary.
    """
    return {"type": "error", "code": code, "message": message}
