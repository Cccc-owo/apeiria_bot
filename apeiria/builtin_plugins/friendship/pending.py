"""Persistence helpers for the friendship request plugin.

Read and write pending requests from a YAML store file, providing a small
async, guarded CRUD interface used by the friendship plugin.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from nonebot import require
from nonebot.log import logger

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_file

from .models import PendingRequest

_STORE_FILE: Path | None = None
_STORE_LOCK = asyncio.Lock()
_TTL = timedelta(days=7)


def _store_path() -> Path:
    """Return the path to the YAML file storing pending requests."""
    global _STORE_FILE  # noqa: PLW0603
    if _STORE_FILE is None:
        _STORE_FILE = get_plugin_data_file("pending_requests.yaml")
    return _STORE_FILE


def _generate_id(pending_list: list[PendingRequest], kind: str) -> str:
    """Generate a unique short request id for the given request kind.

    Args:
        pending_list: The list of existing pending requests.
        kind: The request kind to generate an id for.

    Returns:
        A unique request id not already used in the pending list.
    """
    kind_prefixes = {"friend": "f", "group_add": "g", "group_invite": "g"}
    prefix = kind_prefixes.get(kind, "f")
    existing_ids = {p.id for p in pending_list if p.id}
    while True:
        request_id = f"{prefix}-{uuid.uuid4().hex[:4]}"
        if request_id not in existing_ids:
            return request_id


def _load() -> list[dict]:
    """Load all pending requests from the store file as raw dicts.

    Returns:
        A list of the stored request dicts, or an empty list when the file is
        missing or cannot be parsed.
    """
    path = _store_path()
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:  # noqa: BLE001
        logger.warning("failed to load pending requests, resetting")
    return []


def _save(requests: list[PendingRequest]) -> None:
    """Persist the given pending requests to the store file.

    Args:
        requests: The pending requests to save.
    """
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "id": r.id,
            "provider_key": r.provider_key,
            "bot_self_id": r.bot_self_id,
            "scope": r.scope,
            "raw_flag": r.raw_flag,
            "kind": r.kind,
            "requester_id": r.requester_id,
            "requester_name": r.requester_name,
            "comment": r.comment,
            "sub_type": r.sub_type,
            "group_id": r.group_id,
            "group_name": r.group_name,
            "created_at": r.created_at,
            "status": r.status,
            "notified": r.notified,
        }
        for r in requests
    ]
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


def _data_to_pending(d: dict) -> PendingRequest:
    """Convert a raw stored dict into a PendingRequest.

    Args:
        d: The stored request dict.

    Returns:
        The corresponding PendingRequest.
    """
    return PendingRequest(
        id=d.get("id", ""),
        provider_key=d.get("provider_key", ""),
        bot_self_id=d.get("bot_self_id", ""),
        scope=d.get("scope", ""),
        raw_flag=d.get("raw_flag", ""),
        kind=d.get("kind", "friend"),
        requester_id=d.get("requester_id", ""),
        requester_name=d.get("requester_name", ""),
        comment=d.get("comment", ""),
        sub_type=d.get("sub_type"),
        group_id=d.get("group_id"),
        group_name=d.get("group_name"),
        created_at=d.get("created_at", ""),
        status=d.get("status", "pending"),
        notified=d.get("notified", {}),
    )


async def load_all() -> list[PendingRequest]:
    """Load all pending requests from the store.

    Returns:
        The list of pending requests currently stored.
    """
    async with _STORE_LOCK:
        return [_data_to_pending(d) for d in _load()]


async def add_pending(pending: PendingRequest) -> None:
    """Add a new pending request to the store.

    Assigns a unique id to the request, appends it to the current request
    list, prunes expired entries, and persists the result.

    Args:
        pending: The pending request to add.
    """
    async with _STORE_LOCK:
        items = [_data_to_pending(d) for d in _load()]
        pending.id = _generate_id(items, pending.kind)
        items.append(pending)
        _cleanup(items)
        _save(items)


async def remove_pending(request_id: str) -> bool:
    """Remove the pending request with the given id.

    Args:
        request_id: The id of the request to remove.

    Returns:
        True if a matching request was removed, False otherwise.
    """
    async with _STORE_LOCK:
        items = [_data_to_pending(d) for d in _load()]
        removed = [r for r in items if r.id == request_id]
        items = [r for r in items if r.id != request_id]
        if removed:
            _save(items)
            return True
    return False


async def get_pending(request_id: str) -> PendingRequest | None:
    """Return the pending request with the given id.

    Args:
        request_id: The id of the request to look up.

    Returns:
        The matching pending request, or None when no request has that id.
    """
    async with _STORE_LOCK:
        items = [_data_to_pending(d) for d in _load()]
        for r in items:
            if r.id == request_id:
                return r
    return None


async def update_notified(request_id: str, superuser_id: str, msg_id: str) -> None:
    """Record a notification message for a pending request.

    Stores the given message id under the superuser id in the request's
    notified bookkeeping and persists the change.

    Args:
        request_id: The id of the request to update.
        superuser_id: The superuser key under which to store the message id.
        msg_id: The notification message id to record.
    """
    async with _STORE_LOCK:
        items = [_data_to_pending(d) for d in _load()]
        for r in items:
            if r.id == request_id:
                r.notified[superuser_id] = msg_id
                break
        _save(items)


async def find_by_notified_msg(msg_id: str) -> PendingRequest | None:
    """Return the pending request notified with the given message id.

    Args:
        msg_id: The notification message id to search for.

    Returns:
        The matching pending request, or None when no request recorded it.
    """
    async with _STORE_LOCK:
        items = [_data_to_pending(d) for d in _load()]
        for r in items:
            if msg_id in r.notified.values():
                return r
    return None


def _cleanup(items: list[PendingRequest]) -> None:
    """Drop expired or non-pending requests from the given list.

    Modifies the list in place, keeping only requests whose status is
    ``pending`` and whose creation timestamps fall within the TTL window.

    Args:
        items: The list of pending requests to prune in place.
    """
    cutoff = datetime.now(UTC) - _TTL
    items[:] = [
        r
        for r in items
        if r.status == "pending" and datetime.fromisoformat(r.created_at) > cutoff
    ]
