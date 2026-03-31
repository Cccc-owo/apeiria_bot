"""JWT authentication utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apeiria.infra.config.webui_config import get_web_ui_config
from apeiria.infra.webui_auth.secrets import get_account_by_id, get_token_secret
from apeiria.shared.i18n import t
from apeiria.shared.webui_roles import (
    CAP_ACCOUNT_MANAGE,
    CAP_CONTROL_PANEL,
    ROLE_OWNER,
    capabilities_for_role,
    has_capability,
    normalize_role,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_security = HTTPBearer()


def _raise_invalid_token() -> None:
    raise jwt.InvalidTokenError


def create_token(data: dict[str, Any] | None = None) -> str:
    """Create a JWT token."""
    web_ui_config = get_web_ui_config()
    payload = {
        "exp": datetime.now(timezone.utc)
        + timedelta(days=web_ui_config.token_expire_days),
        "iat": datetime.now(timezone.utc),
        "sub": "webui",
        **(data or {}),
    }
    return jwt.encode(payload, get_token_secret(), algorithm="HS256")


def verify_token(token: str) -> dict[str, Any]:
    """Verify a JWT token. Raises HTTPException on failure."""
    try:
        claims = jwt.decode(token, get_token_secret(), algorithms=["HS256"])
        user_id = str(claims.get("user_id") or "")
        account = get_account_by_id(user_id) if user_id else None
        if account is None:
            _raise_invalid_token()
        assert account is not None
        if account.is_disabled:
            _raise_invalid_token()
        token_session_version = int(claims.get("session_version") or 0)
        if token_session_version != account.session_version:
            _raise_invalid_token()
        claims["user_id"] = account.user_id
        claims["username"] = account.username
        claims["role"] = normalize_role(account.role)
        claims["capabilities"] = capabilities_for_role(account.role)
        claims["session_version"] = account.session_version
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.token_expired"),
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.token_invalid"),
        ) from None
    else:
        return claims


async def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_security)],
) -> dict[str, Any]:
    """Require a valid JWT bearer token."""
    return verify_token(credentials.credentials)


async def require_optional_auth(request: Request) -> dict[str, Any]:
    """Require a bearer token when headers are handled manually."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.token_invalid"),
        )
    return verify_token(token)


def require_role(
    required_role: str,
) -> Callable[..., Any]:
    """Build a dependency that requires the current user to have a minimum role."""

    async def _require_role(
        claims: Annotated[dict[str, Any], Depends(require_auth)],
    ) -> dict[str, Any]:
        actual_role = normalize_role(claims.get("role"))
        if actual_role != normalize_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=t("web_ui.auth.permission_denied"),
            )
        claims["role"] = actual_role
        return claims

    return _require_role


require_owner = require_role(ROLE_OWNER)


def require_capability(
    capability: str,
) -> Callable[..., Any]:
    """Build a dependency that requires one control-panel capability."""

    async def _require_capability(
        claims: Annotated[dict[str, Any], Depends(require_auth)],
    ) -> dict[str, Any]:
        role = normalize_role(claims.get("role"))
        if not has_capability(role, capability):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=t("web_ui.auth.permission_denied"),
            )
        claims["role"] = role
        claims["capabilities"] = capabilities_for_role(role)
        return claims

    return _require_capability


require_control_panel = require_capability(CAP_CONTROL_PANEL)
require_account_manage = require_capability(CAP_ACCOUNT_MANAGE)
