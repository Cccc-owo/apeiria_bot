"""Auth routes — login endpoint."""

from fastapi import APIRouter, HTTPException, status

from apeiria.core.i18n import t
from apeiria.plugins.web_ui.auth import create_token
from apeiria.plugins.web_ui.models import LoginRequest, LoginResponse
from apeiria.plugins.web_ui.secrets import get_password

router = APIRouter()


@router.post("/login")
async def login(body: LoginRequest) -> LoginResponse:
    if body.password != get_password():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("web_ui.auth.wrong_password"),
        )
    return LoginResponse(token=create_token())
