"""JWT authentication utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apeiria.core.configs.config import bot_config
from apeiria.core.i18n import t

from .secrets import get_token_secret

_security = HTTPBearer()


def create_token(data: dict[str, Any] | None = None) -> str:
    """Create a JWT token."""
    payload = {
        "exp": datetime.now(timezone.utc)
        + timedelta(days=bot_config.web_ui_token_expire_days),
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
