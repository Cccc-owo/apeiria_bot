"""Authentication routes for the Web UI."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apeiria.infra.webui_auth.secrets import (
    get_account_by_id,
    list_security_audit_events,
    record_login_success,
    register_account,
    rotate_account_session_version,
    update_account_password,
    verify_account_password,
)
from apeiria.interfaces.http.auth import (
    create_token,
    require_auth,
    require_control_panel,
)
from apeiria.interfaces.http.login_guard import (
    is_login_allowed,
    record_login_failure,
)
from apeiria.interfaces.http.login_guard import (
    record_login_success as clear_login_failures,
)
from apeiria.interfaces.http.schemas.models import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RegisterRequest,
    RegisterResponse,
    SecurityAuditEventItem,
    SessionRefreshResponse,
    WebUIAccountItem,
    WebUIPrincipalResponse,
)
from apeiria.shared.i18n import t
from apeiria.shared.webui_roles import (
    can_access_control_panel,
    capabilities_for_role,
    normalize_role,
)

router = APIRouter()


def _to_webui_principal_response(
    *,
    user_id: str,
    username: str,
    role: str,
) -> WebUIPrincipalResponse:
    return WebUIPrincipalResponse(
        user_id=user_id,
        username=username,
        role=role,
        capabilities=capabilities_for_role(role),
    )


@router.post("/login")
async def login(body: LoginRequest, request: Request) -> LoginResponse:
    """Authenticate a Web UI account and return a JWT token."""
    client_ip = request.client.host if request.client else ""
    if not is_login_allowed(body.username, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=t("web_ui.auth.login_temporarily_locked"),
        )
    account = verify_account_password(body.username, body.password)
    if account is None:
        record_login_failure(body.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.invalid_credentials"),
        )
    if not can_access_control_panel(account.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("web_ui.auth.permission_denied"),
        )
    clear_login_failures(account.username, client_ip)
    account = record_login_success(account.user_id) or account
    principal = account.to_principal()
    return LoginResponse(
        token=create_token(
            {
                "sub": principal.username,
                "user_id": principal.user_id,
                "username": principal.username,
                "role": principal.role,
                "capabilities": capabilities_for_role(principal.role),
                "session_version": account.session_version,
                "client_ip": client_ip,
            }
        ),
        principal=_to_webui_principal_response(
            user_id=principal.user_id,
            username=principal.username,
            role=principal.role,
        ),
    )


@router.post("/register")
async def register(body: RegisterRequest) -> RegisterResponse:
    """Register a new Web UI account with a one-time registration code."""
    try:
        register_account(body.registration_code, body.username, body.password)
    except ValueError as exc:
        error_code = str(exc)
        detail_key = {
            "registration_code_invalid": "web_ui.auth.registration_code_invalid",
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
    role = normalize_role(claims.get("role"))
    if not can_access_control_panel(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("web_ui.auth.permission_denied"),
        )
    return _to_webui_principal_response(
        user_id=str(claims.get("user_id") or claims.get("sub") or "webui"),
        username=str(claims.get("username") or claims.get("sub") or "webui"),
        role=role,
    )


@router.get("/me/account")
async def get_current_account(
    claims: Annotated[dict[str, Any], Depends(require_control_panel)],
) -> WebUIAccountItem:
    """Return the current account record."""
    user_id = str(claims.get("user_id") or "")
    account = get_account_by_id(user_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("web_ui.auth.account_not_found"),
        )
    return WebUIAccountItem(
        user_id=account.user_id,
        username=account.username,
        role=account.role,
        is_disabled=account.is_disabled,
        last_login_at=account.last_login_at,
        password_changed_at=account.password_changed_at,
    )


@router.get("/audit-events")
async def get_security_audit_events(
    _: Annotated[Any, Depends(require_control_panel)],
) -> list[SecurityAuditEventItem]:
    """List recent security audit events."""
    return [
        SecurityAuditEventItem(
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            actor_username=event.actor_username,
            target_username=event.target_username,
            detail=event.detail,
        )
        for event in list_security_audit_events()
    ]


@router.post("/password")
async def change_password(
    body: PasswordChangeRequest,
    claims: Annotated[dict[str, Any], Depends(require_control_panel)],
) -> SessionRefreshResponse:
    """Change the current account password."""
    username = str(claims.get("username") or claims.get("sub") or "")
    user_id = str(claims.get("user_id") or "")
    if body.current_password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("web_ui.auth.current_password_required"),
        )
    account = verify_account_password(username, body.current_password)
    if account is None or account.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.invalid_credentials"),
        )
    updated_account = update_account_password(user_id, body.new_password)
    if updated_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("web_ui.auth.account_not_found"),
        )
    updated_principal = updated_account.to_principal()
    return SessionRefreshResponse(
        detail=t("web_ui.auth.password_changed"),
        token=create_token(
            {
                "sub": updated_principal.username,
                "user_id": updated_principal.user_id,
                "username": updated_principal.username,
                "role": updated_principal.role,
                "capabilities": capabilities_for_role(updated_principal.role),
                "session_version": updated_account.session_version,
            }
        ),
        principal=_to_webui_principal_response(
            user_id=updated_principal.user_id,
            username=updated_principal.username,
            role=updated_principal.role,
        ),
    )


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    claims: Annotated[dict[str, Any], Depends(require_control_panel)],
) -> SessionRefreshResponse:
    """Invalidate previous sessions and return a fresh token for the current account."""
    user_id = str(claims.get("user_id") or "")
    actor_username = str(claims.get("username") or claims.get("sub") or "")
    updated_account = rotate_account_session_version(
        user_id,
        actor_username=actor_username,
    )
    if updated_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("web_ui.auth.account_not_found"),
        )
    updated_principal = updated_account.to_principal()
    return SessionRefreshResponse(
        detail=t("web_ui.auth.sessions_revoked"),
        token=create_token(
            {
                "sub": updated_principal.username,
                "user_id": updated_principal.user_id,
                "username": updated_principal.username,
                "role": updated_principal.role,
                "capabilities": capabilities_for_role(updated_principal.role),
                "session_version": updated_account.session_version,
            }
        ),
        principal=_to_webui_principal_response(
            user_id=updated_principal.user_id,
            username=updated_principal.username,
            role=updated_principal.role,
        ),
    )
