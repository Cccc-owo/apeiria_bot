"""Authentication routes for the Web UI."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from apeiria.core.i18n import t
from apeiria.plugins.web_ui.auth import create_token, require_auth
from apeiria.plugins.web_ui.models import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    WebUIPrincipalResponse,
)
from apeiria.plugins.web_ui.secrets import register_account, verify_account_password

router = APIRouter()


@router.post("/login")
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate a Web UI account and return a JWT token."""
    account = verify_account_password(body.username, body.password)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.invalid_credentials"),
        )
    principal = account.to_principal()
    return LoginResponse(
        token=create_token(
            {
                "sub": principal.username,
                "user_id": principal.user_id,
                "username": principal.username,
                "role": principal.role,
            }
        ),
        principal=principal,
    )


@router.post("/register")
async def register(body: RegisterRequest) -> RegisterResponse:
    """Register a new Web UI account with a one-time registration code."""
    try:
        register_account(body.invite_code, body.username, body.password)
    except ValueError as exc:
        error_code = str(exc)
        detail_key = {
            "invite_invalid": "web_ui.auth.invite_invalid",
            "username_invalid": "web_ui.auth.username_invalid",
            "username_taken": "web_ui.auth.username_taken",
        }.get(error_code, "web_ui.auth.register_failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t(detail_key),
        ) from None
    return RegisterResponse(detail=t("web_ui.auth.register_success"))


@router.get("/me")
async def get_current_user(
    claims: Annotated[Any, Depends(require_auth)],
) -> WebUIPrincipalResponse:
    """Return the current authenticated user."""
    return WebUIPrincipalResponse(
        user_id=str(claims.get("user_id") or claims.get("sub") or "webui"),
        username=str(claims.get("username") or claims.get("sub") or "webui"),
        role=str(claims.get("role") or "admin"),
    )
