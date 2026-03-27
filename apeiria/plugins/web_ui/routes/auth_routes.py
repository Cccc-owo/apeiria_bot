"""Authentication routes for the Web UI."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from apeiria.core.i18n import t
from apeiria.plugins.web_ui.auth import (
    create_token,
    require_account_manage,
    require_auth,
    require_control_panel,
    require_owner,
)
from apeiria.plugins.web_ui.models import (
    LoginRequest,
    LoginResponse,
    OperationStatusResponse,
    PasswordChangeRequest,
    RegisterRequest,
    RegisterResponse,
    RegistrationCodeCreateRequest,
    RegistrationCodeItem,
    RoleUpdateRequest,
    WebUIAccountItem,
    WebUIPrincipalResponse,
)
from apeiria.plugins.web_ui.roles import (
    ROLE_OWNER,
    SUPPORTED_ASSIGNABLE_ROLES,
    can_access_control_panel,
    capabilities_for_role,
    normalize_role,
)
from apeiria.plugins.web_ui.secrets import (
    create_registration_code,
    list_accounts,
    list_registration_codes,
    register_account,
    revoke_registration_code,
    update_account_password,
    update_account_role,
    verify_account_password,
)

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
    if not can_access_control_panel(account.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("web_ui.auth.permission_denied"),
        )
    principal = account.to_principal()
    return LoginResponse(
        token=create_token(
            {
                "sub": principal.username,
                "user_id": principal.user_id,
                "username": principal.username,
                "role": principal.role,
                "capabilities": capabilities_for_role(principal.role),
            }
        ),
        principal=WebUIPrincipalResponse(
            user_id=principal.user_id,
            username=principal.username,
            role=principal.role,
            capabilities=capabilities_for_role(principal.role),
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
    return WebUIPrincipalResponse(
        user_id=str(claims.get("user_id") or claims.get("sub") or "webui"),
        username=str(claims.get("username") or claims.get("sub") or "webui"),
        role=role,
        capabilities=capabilities_for_role(role),
    )


@router.get("/accounts")
async def get_accounts(
    _: Annotated[Any, Depends(require_account_manage)],
) -> list[WebUIAccountItem]:
    """List Web UI accounts."""
    return [
        WebUIAccountItem(
            user_id=account.user_id,
            username=account.username,
            role=account.role,
            is_disabled=account.is_disabled,
        )
        for account in list_accounts()
    ]


@router.get("/registration-codes")
async def get_registration_codes(
    _: Annotated[Any, Depends(require_account_manage)],
) -> list[RegistrationCodeItem]:
    """List active registration codes."""
    return [
        RegistrationCodeItem(
            code=registration_code.code,
            role=registration_code.role,
            created_at=registration_code.created_at,
            created_by=registration_code.created_by,
        )
        for registration_code in list_registration_codes()
    ]


@router.post("/registration-codes")
async def create_registration_code_route(
    body: RegistrationCodeCreateRequest,
    claims: Annotated[dict[str, Any], Depends(require_account_manage)],
) -> RegistrationCodeItem:
    """Create one registration code."""
    requested_role = body.role.strip().lower()
    if requested_role not in SUPPORTED_ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("web_ui.auth.invalid_role"),
        )
    role = normalize_role(requested_role)
    if role == ROLE_OWNER and normalize_role(claims.get("role")) != ROLE_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("web_ui.auth.permission_denied"),
        )

    registration_code = create_registration_code(
        role=role,
        created_by=str(claims.get("username") or claims.get("sub") or "unknown"),
    )
    return RegistrationCodeItem(
        code=registration_code.code,
        role=registration_code.role,
        created_at=registration_code.created_at,
        created_by=registration_code.created_by,
    )


@router.delete("/registration-codes/{code}")
async def delete_registration_code(
    code: str,
    _: Annotated[Any, Depends(require_account_manage)],
) -> OperationStatusResponse:
    """Revoke one registration code."""
    if not revoke_registration_code(code):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("web_ui.auth.registration_code_not_found"),
        )
    return OperationStatusResponse(detail=t("web_ui.auth.registration_code_revoked"))


@router.post("/password")
async def change_password(
    body: PasswordChangeRequest,
    claims: Annotated[dict[str, Any], Depends(require_control_panel)],
) -> OperationStatusResponse:
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
    update_account_password(user_id, body.new_password)
    return OperationStatusResponse(detail=t("web_ui.auth.password_changed"))


@router.patch("/accounts/{user_id}/role")
async def update_role(
    user_id: str,
    body: RoleUpdateRequest,
    claims: Annotated[dict[str, Any], Depends(require_owner)],
) -> WebUIAccountItem:
    """Change one account role."""
    requested_role = body.role.strip().lower()
    if requested_role not in SUPPORTED_ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("web_ui.auth.invalid_role"),
        )
    role = normalize_role(requested_role)
    current_user_id = str(claims.get("user_id") or "")
    if current_user_id == user_id and role != ROLE_OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("web_ui.auth.owner_self_demotion_forbidden"),
        )
    account = update_account_role(user_id, role)
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
    )
