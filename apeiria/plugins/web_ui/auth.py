"""JWT authentication utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apeiria.core.i18n import t

from .config import get_web_ui_config
from .secrets import get_token_secret

_security = HTTPBearer()


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
        return jwt.decode(token, get_token_secret(), algorithms=["HS256"])
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


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict[str, Any]:
    """FastAPI dependency: require valid JWT token."""
    return verify_token(credentials.credentials)


async def require_optional_auth(request: Request) -> dict[str, Any]:
    """FastAPI dependency: require a bearer token when headers are handled manually."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.token_invalid"),
        )
    return verify_token(token)
