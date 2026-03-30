from __future__ import annotations

import contextlib
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import nonebot

from apeiria.config import project_config_service
from apeiria.core.utils.files import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path

_PASSWORD_HASH_N = 2**14
_PASSWORD_HASH_R = 8
_PASSWORD_HASH_P = 1
_PASSWORD_HASH_LEN = 64
_PASSWORD_MIN_LENGTH = 8
_PASSWORD_MAX_LENGTH = 128
_SUPPORTED_ROLES = {"owner"}


@dataclass(frozen=True)
class HostWebUIAccount:
    username: str
    role: str
    is_disabled: bool
    last_login_at: str | None = None
    password_changed_at: str | None = None


@dataclass(frozen=True)
class HostRegistrationCode:
    code: str
    role: str
    created_by: str
    created_at: str


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in _SUPPORTED_ROLES:
        raise ValueError("invalid_role")
    return normalized


def _hash_password(password: str, *, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=actual_salt.encode("utf-8"),
        n=_PASSWORD_HASH_N,
        r=_PASSWORD_HASH_R,
        p=_PASSWORD_HASH_P,
        dklen=_PASSWORD_HASH_LEN,
    )
    return f"scrypt${actual_salt}${derived.hex()}"


def _validate_password(password: str) -> None:
    if not (_PASSWORD_MIN_LENGTH <= len(password) <= _PASSWORD_MAX_LENGTH):
        raise ValueError("password_invalid")


def _apply_secret_permissions(secret_file: "Path") -> None:
    with contextlib.suppress(OSError):
        secret_file.chmod(0o600)


def _record_audit_event(
    data: dict[str, Any],
    event_type: str,
    *,
    actor_username: str | None = None,
    target_username: str | None = None,
    detail: str | None = None,
) -> None:
    current_events = [
        item for item in data.get("audit_events", []) if isinstance(item, dict)
    ]
    current_events.append(
        {
            "event_type": event_type,
            "occurred_at": _iso_now(),
            "actor_username": actor_username,
            "target_username": target_username,
            "detail": detail,
        }
    )
    data["audit_events"] = current_events[-100:]


def _new_registration_code(*, role: str, created_by: str) -> dict[str, str]:
    return {
        "code": secrets.token_urlsafe(32),
        "role": role,
        "created_by": created_by,
        "created_at": _iso_now(),
    }


def _ensure_bootstrap_registration_code(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure there is one bootstrap registration code when auth is fully empty."""
    if _users(data) or _registration_codes(data):
        return data
    data["registration_codes"] = [
        _new_registration_code(role="owner", created_by="system")
    ]
    return data


def _with_bootstrap_registration_code(
    data: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Return normalized auth data and whether bootstrap code was injected."""
    had_users = bool(_users(data))
    had_codes = bool(_registration_codes(data))
    normalized = _ensure_bootstrap_registration_code(data)
    return normalized, not had_users and not had_codes


def _load_auth_store() -> dict[str, Any]:
    secret_file = _get_secret_file()
    if not secret_file.exists():
        data = {
            "token_secret": secrets.token_urlsafe(32),
            "users": [],
            "registration_codes": [],
            "audit_events": [],
        }
        data = _ensure_bootstrap_registration_code(data)
        _persist_auth_store(data)
        return data

    try:
        data = json.loads(secret_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = "web_ui auth storage is corrupted"
        raise RuntimeError(msg) from exc
    except OSError as exc:
        msg = "web_ui auth storage is unreadable"
        raise RuntimeError(msg) from exc

    if not isinstance(data, dict) or "token_secret" not in data:
        msg = "web_ui auth storage has unsupported schema"
        raise RuntimeError(msg)
    data, changed = _with_bootstrap_registration_code(data)
    if changed:
        _persist_auth_store(data)
    return data


def _persist_auth_store(data: dict[str, Any]) -> None:
    secret_file = _get_secret_file()
    atomic_write_text(secret_file, json.dumps(data, ensure_ascii=True, indent=2))
    _apply_secret_permissions(secret_file)


def _get_secret_file():
    """Resolve the Web UI auth file via nonebot_plugin_localstore."""
    try:
        nonebot.get_driver()
    except ValueError:
        nonebot.init(**project_config_service.get_project_config_kwargs())
    from nonebot_plugin_localstore import get_data_file

    return get_data_file("web_ui", "secret.json")


def _users(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in data.get("users", []) if isinstance(item, dict)]


def _registration_codes(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in data.get("registration_codes", []) if isinstance(item, dict)
    ]


def _find_user(data: dict[str, Any], username: str) -> dict[str, Any] | None:
    normalized_username = _normalize_username(username)
    return next(
        (
            item
            for item in _users(data)
            if str(item.get("username") or "") == normalized_username
        ),
        None,
    )


def _enabled_owner_count(data: dict[str, Any]) -> int:
    return sum(
        1
        for item in _users(data)
        if str(item.get("role") or "") == "owner" and not bool(item.get("is_disabled"))
    )


def list_accounts() -> list[HostWebUIAccount]:
    """Return host-side Web UI accounts."""
    data = _load_auth_store()
    return [
        HostWebUIAccount(
            username=str(item.get("username") or ""),
            role=str(item.get("role") or "owner"),
            is_disabled=bool(item.get("is_disabled", False)),
            last_login_at=(
                str(item.get("last_login_at"))
                if item.get("last_login_at") is not None
                else None
            ),
            password_changed_at=(
                str(item.get("password_changed_at"))
                if item.get("password_changed_at") is not None
                else None
            ),
        )
        for item in _users(data)
    ]


def create_account(username: str, password: str, *, role: str = "owner") -> str:
    """Create one Web UI account from the host."""
    normalized_username = _normalize_username(username)
    if not normalized_username:
        raise ValueError("username_invalid")
    _validate_password(password)
    normalized_role = _normalize_role(role)
    data = _load_auth_store()
    if _find_user(data, normalized_username) is not None:
        raise ValueError("username_taken")
    users = _users(data)
    users.append(
        {
            "user_id": f"webui_{secrets.token_hex(8)}",
            "username": normalized_username,
            "password_hash": _hash_password(password),
            "role": normalized_role,
            "is_disabled": False,
            "password_changed_at": _iso_now(),
            "session_version": 0,
        }
    )
    data["users"] = users
    _record_audit_event(
        data,
        "account_created",
        actor_username="host",
        target_username=normalized_username,
    )
    _persist_auth_store(data)
    return normalized_username


def set_account_password(username: str, password: str) -> str:
    """Reset one Web UI account password from the host."""
    _validate_password(password)
    data = _load_auth_store()
    item = _find_user(data, username)
    if item is None:
        raise ValueError("account_not_found")
    item["password_hash"] = _hash_password(password)
    item["password_changed_at"] = _iso_now()
    item["session_version"] = int(item.get("session_version") or 0) + 1
    item["is_disabled"] = False
    data["users"] = _users(data)
    _record_audit_event(
        data,
        "password_changed",
        actor_username="host",
        target_username=str(item.get("username") or ""),
    )
    _persist_auth_store(data)
    return str(item.get("username") or "")


def set_account_disabled(username: str, *, disabled: bool) -> str:
    """Enable or disable one Web UI account from the host."""
    data = _load_auth_store()
    item = _find_user(data, username)
    if item is None:
        raise ValueError("account_not_found")
    if (
        disabled
        and str(item.get("role") or "") == "owner"
        and not bool(item.get("is_disabled", False))
        and _enabled_owner_count(data) <= 1
    ):
        raise ValueError("last_owner_forbidden")
    item["is_disabled"] = disabled
    item["session_version"] = int(item.get("session_version") or 0) + 1
    data["users"] = _users(data)
    _record_audit_event(
        data,
        "account_disabled" if disabled else "account_enabled",
        actor_username="host",
        target_username=str(item.get("username") or ""),
    )
    _persist_auth_store(data)
    return str(item.get("username") or "")


def delete_account(username: str) -> str:
    """Delete one Web UI account from the host."""
    data = _load_auth_store()
    item = _find_user(data, username)
    if item is None:
        raise ValueError("account_not_found")
    if (
        str(item.get("role") or "") == "owner"
        and not bool(item.get("is_disabled", False))
        and _enabled_owner_count(data) <= 1
    ):
        raise ValueError("last_owner_forbidden")
    normalized_username = str(item.get("username") or "")
    data["users"] = [
        user
        for user in _users(data)
        if str(user.get("username") or "") != normalized_username
    ]
    _record_audit_event(
        data,
        "account_deleted",
        actor_username="host",
        target_username=normalized_username,
    )
    _persist_auth_store(data)
    return normalized_username


def list_registration_codes() -> list[HostRegistrationCode]:
    """Return host-side Web UI registration codes."""
    data = _load_auth_store()
    return [
        HostRegistrationCode(
            code=str(item.get("code") or ""),
            role=str(item.get("role") or "owner"),
            created_by=str(item.get("created_by") or "unknown"),
            created_at=str(item.get("created_at") or ""),
        )
        for item in _registration_codes(data)
    ]


def create_registration_code(
    *,
    role: str = "owner",
    created_by: str = "host",
) -> HostRegistrationCode:
    """Create one host-side registration code."""
    normalized_role = _normalize_role(role)
    data = _load_auth_store()
    item = {
        **_new_registration_code(role=normalized_role, created_by=created_by),
        "role": normalized_role,
    }
    codes = _registration_codes(data)
    codes.append(item)
    data["registration_codes"] = codes
    _record_audit_event(
        data,
        "registration_code_created",
        actor_username=created_by,
        detail=normalized_role,
    )
    _persist_auth_store(data)
    return HostRegistrationCode(
        code=str(item["code"]),
        role=str(item["role"]),
        created_by=str(item["created_by"]),
        created_at=str(item["created_at"]),
    )


def revoke_registration_code(code: str) -> str:
    """Revoke one host-side registration code."""
    normalized_code = code.strip()
    data = _load_auth_store()
    codes = _registration_codes(data)
    if not any(str(item.get("code") or "") == normalized_code for item in codes):
        raise ValueError("registration_code_not_found")
    data["registration_codes"] = [
        item for item in codes if str(item.get("code") or "") != normalized_code
    ]
    _record_audit_event(
        data,
        "registration_code_revoked",
        actor_username="host",
        detail=None,
    )
    _persist_auth_store(data)
    return normalized_code


def recover_owner_account(username: str, password: str) -> tuple[str, bool]:
    """Create or recover one owner account without bootstrapping NoneBot."""
    normalized_username = _normalize_username(username)
    if not normalized_username:
        raise ValueError("username_invalid")
    _validate_password(password)

    data = _load_auth_store()
    users = [item for item in data.get("users", []) if isinstance(item, dict)]

    for item in users:
        if str(item.get("username") or "") != normalized_username:
            continue
        item["password_hash"] = _hash_password(password)
        item["password_changed_at"] = _iso_now()
        item["session_version"] = int(item.get("session_version") or 0) + 1
        item["role"] = "owner"
        item["is_disabled"] = False
        _record_audit_event(
            data,
            "owner_account_recovered",
            actor_username="host",
            target_username=normalized_username,
        )
        data["users"] = users
        _persist_auth_store(data)
        return normalized_username, False

    users.append(
        {
            "user_id": f"webui_{secrets.token_hex(8)}",
            "username": normalized_username,
            "password_hash": _hash_password(password),
            "role": "owner",
            "is_disabled": False,
            "password_changed_at": _iso_now(),
            "session_version": 0,
        }
    )
    data["users"] = users
    _record_audit_event(
        data,
        "owner_account_recovered",
        actor_username="host",
        target_username=normalized_username,
    )
    _persist_auth_store(data)
    return normalized_username, True
