"""Persistent Web UI authentication storage."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nonebot.log import logger
from nonebot_plugin_localstore import get_data_file

from apeiria.core.i18n import t
from apeiria.core.utils.files import atomic_write_text

from .models import WebUIPrincipalResponse

_PLUGIN_DATA_ID = "apeiria.plugins.web_ui"
_PASSWORD_HASH_N = 2**14
_PASSWORD_HASH_R = 8
_PASSWORD_HASH_P = 1
_PASSWORD_HASH_LEN = 64

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class WebUIAccount:
    """Stored Web UI account."""

    user_id: str
    username: str
    password_hash: str
    role: str = "admin"

    def to_principal(self) -> WebUIPrincipalResponse:
        """Convert the account into the API principal shape."""
        return WebUIPrincipalResponse(
            user_id=self.user_id,
            username=self.username,
            role=self.role,
        )


def _apply_secret_permissions(secret_file: "Path") -> None:
    with contextlib.suppress(OSError):
        secret_file.chmod(0o600)


def _hash_password(password: str, *, salt: str | None = None) -> str:
    """Hash a password with scrypt and return an encoded storage string."""
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


def _verify_password_hash(password: str, encoded: str) -> bool:
    """Validate a plaintext password against the stored scrypt hash."""
    algorithm, _, payload = encoded.partition("$")
    if algorithm != "scrypt" or "$" not in payload:
        return False
    salt, _, _expected = payload.partition("$")
    actual = _hash_password(password, salt=salt)
    return hmac.compare_digest(actual, encoded)


def _normalize_username(username: str) -> str:
    """Normalize usernames for storage and comparison."""
    return username.strip().lower()


def _load_or_create_raw() -> dict[str, Any]:
    """Load raw auth storage from disk, creating a default document when missing."""
    secret_file = get_data_file(_PLUGIN_DATA_ID, "secret.json")
    if secret_file.is_file():
        try:
            data = json.loads(secret_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.opt(exception=exc).critical(
                "Web UI auth storage is corrupted: {}",
                secret_file,
            )
            msg = (
                "web_ui auth storage is corrupted; "
                "fix or restore secret.json before startup"
            )
            raise RuntimeError(msg) from exc
        except OSError as exc:
            logger.opt(exception=exc).critical(
                "Failed to read Web UI auth storage: {}",
                secret_file,
            )
            msg = "web_ui auth storage is unreadable"
            raise RuntimeError(msg) from exc

        if isinstance(data, dict) and "token_secret" in data:
            upgraded = _upgrade_legacy_schema(data)
            _persist_raw(upgraded)
            return upgraded

        logger.critical("Web UI auth storage has unsupported schema: {}", secret_file)
        msg = "web_ui auth storage has unsupported schema"
        raise RuntimeError(msg)

    data = {
        "token_secret": secrets.token_urlsafe(32),
        "users": [],
        "invite_codes": [secrets.token_urlsafe(12)],
    }
    _persist_raw(data)
    logger.info("{}", t("web_ui.secrets.generated"))
    return data


def _upgrade_legacy_schema(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade legacy single-password storage into the current account schema."""
    users = data.get("users")
    invite_codes = data.get("invite_codes")
    if isinstance(users, list) and isinstance(invite_codes, list):
        return data

    upgraded = {
        "token_secret": str(data["token_secret"]),
        "users": [],
        "invite_codes": [secrets.token_urlsafe(12)],
    }
    legacy_password = data.get("password")
    if isinstance(legacy_password, str) and legacy_password:
        upgraded["users"].append(
            {
                "user_id": "webui_admin",
                "username": "admin",
                "password_hash": _hash_password(legacy_password),
                "role": "admin",
            }
        )
    return upgraded


def _persist_raw(data: dict[str, Any]) -> None:
    """Persist auth storage to disk."""
    secret_file = get_data_file(_PLUGIN_DATA_ID, "secret.json")
    atomic_write_text(
        secret_file,
        json.dumps(data, ensure_ascii=True, indent=2),
    )
    _apply_secret_permissions(secret_file)


_auth_store = _load_or_create_raw()


def get_token_secret() -> str:
    """Return the JWT signing secret."""
    return str(_auth_store["token_secret"])


def get_secret_file_path() -> "Path":
    """Return the auth storage file path."""
    return get_data_file(_PLUGIN_DATA_ID, "secret.json")


def list_accounts() -> list[WebUIAccount]:
    """List all stored Web UI accounts."""
    accounts: list[WebUIAccount] = []
    for item in _auth_store.get("users", []):
        if not isinstance(item, dict):
            continue
        try:
            accounts.append(
                WebUIAccount(
                    user_id=str(item["user_id"]),
                    username=str(item["username"]),
                    password_hash=str(item["password_hash"]),
                    role=str(item.get("role") or "admin"),
                )
            )
        except KeyError:
            continue
    return accounts


def get_account_by_username(username: str) -> WebUIAccount | None:
    """Look up an account by normalized username."""
    normalized = _normalize_username(username)
    return next(
        (account for account in list_accounts() if account.username == normalized),
        None,
    )


def verify_account_password(username: str, password: str) -> WebUIAccount | None:
    """Verify credentials and return the matching account when valid."""
    account = get_account_by_username(username)
    if account is None:
        return None
    if not _verify_password_hash(password, account.password_hash):
        return None
    return account


def register_account(invite_code: str, username: str, password: str) -> WebUIAccount:
    """Create a new account by consuming one registration code."""
    normalized_invite = invite_code.strip()
    available_invites = [
        str(item).strip()
        for item in _auth_store.get("invite_codes", [])
        if isinstance(item, str)
    ]
    if normalized_invite not in available_invites:
        raise ValueError("invite_invalid")

    normalized_username = _normalize_username(username)
    if not normalized_username:
        raise ValueError("username_invalid")
    if get_account_by_username(normalized_username) is not None:
        raise ValueError("username_taken")

    account = WebUIAccount(
        user_id=f"webui_{secrets.token_hex(8)}",
        username=normalized_username,
        password_hash=_hash_password(password),
        role="admin",
    )
    _auth_store["users"] = [
        *[item for item in _auth_store.get("users", []) if isinstance(item, dict)],
        {
            "user_id": account.user_id,
            "username": account.username,
            "password_hash": account.password_hash,
            "role": account.role,
        },
    ]
    _auth_store["invite_codes"] = [
        item for item in available_invites if item != normalized_invite
    ]
    _persist_raw(_auth_store)
    return account
