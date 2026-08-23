"""Data models for the friendship request plugin.

Define the request information extracted from events, the stored pending
request record, and the outcome of an approve/reject operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

RequestKind = Literal["friend", "group_add", "group_invite"]


@dataclass
class RequestInfo:
    """Information extracted from a friendship request event.

    Carries the kind of request together with the requester details and
    any group or comment context reported by the source event.
    """

    kind: RequestKind
    requester_id: str
    requester_name: str
    platform: str
    raw_flag: str
    group_id: str | None = None
    group_name: str | None = None
    comment: str = ""
    sub_type: str | None = None


@dataclass
class PendingRequest:
    """A stored pending friendship or group request.

    Persists the metadata needed to later approve or reject the request,
    together with a status and notification bookkeeping.
    """

    id: str
    provider_key: str
    bot_self_id: str
    scope: str
    raw_flag: str
    kind: RequestKind
    requester_id: str
    requester_name: str
    comment: str = ""
    sub_type: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    notified: dict[str, str] = field(default_factory=dict)


@dataclass
class ProcResult:
    """The result of an approve or reject operation."""

    success: bool
    message: str = ""
