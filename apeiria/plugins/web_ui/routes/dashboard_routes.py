"""Dashboard routes — bot status overview."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from apeiria.core.i18n import t
from apeiria.domains.dashboard import dashboard_service
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import (
    DashboardEventItem,
    DashboardEventsResponse,
    OperationStatusResponse,
    StatusResponse,
)

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status(_: Annotated[Any, Depends(require_auth)]) -> StatusResponse:
    """Return the current dashboard status snapshot."""
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


@router.get("/events", response_model=DashboardEventsResponse)
async def get_events(
    _: Annotated[Any, Depends(require_auth)],
) -> DashboardEventsResponse:
    """Return recent warning and error events for the dashboard."""
    return DashboardEventsResponse(
        items=[
            DashboardEventItem(
                timestamp=item.timestamp,
                level=item.level,
                source=item.source,
                message=item.message,
            )
            for item in dashboard_service.get_recent_events()
        ]
    )


@router.post("/restart", response_model=OperationStatusResponse)
async def restart_bot(
    _: Annotated[Any, Depends(require_auth)],
) -> OperationStatusResponse:
    dashboard_service.schedule_restart()
    return OperationStatusResponse(detail=t("web_ui.dashboard.restart_scheduled"))
