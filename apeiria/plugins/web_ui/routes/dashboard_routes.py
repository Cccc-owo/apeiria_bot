"""Dashboard routes — bot status overview."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from apeiria.core.i18n import t
from apeiria.domains.dashboard import dashboard_service
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import OperationStatusResponse, StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status(_: Annotated[Any, Depends(require_auth)]) -> StatusResponse:
    snapshot = await dashboard_service.get_status_snapshot()
    return StatusResponse(
        status=snapshot.status,
        uptime=snapshot.uptime,
        plugins_count=snapshot.plugins_count,
        disabled_plugins_count=snapshot.disabled_plugins_count,
        groups_count=snapshot.groups_count,
        disabled_groups_count=snapshot.disabled_groups_count,
        bans_count=snapshot.bans_count,
        adapters=snapshot.adapters,
    )


@router.post("/restart", response_model=OperationStatusResponse)
async def restart_bot(
    _: Annotated[Any, Depends(require_auth)],
) -> OperationStatusResponse:
    dashboard_service.schedule_restart()
    return OperationStatusResponse(detail=t("web_ui.dashboard.restart_scheduled"))
