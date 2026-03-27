"""Generic data browser routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from apeiria.domains.data import data_browser_service
from apeiria.domains.exceptions import ResourceNotFoundError
from apeiria.plugins.web_ui.auth import require_control_panel
from apeiria.plugins.web_ui.models import (
    DataListResponse,
    DataRecordResponse,
    DataTableInfo,
)

router = APIRouter()


@router.get("/", response_model=list[DataTableInfo])
async def list_tables(
    _: Annotated[Any, Depends(require_control_panel)],
) -> list[DataTableInfo]:
    return [
        DataTableInfo(
            name=table.name,
            label=table.label,
            primary_key=table.primary_key,
        )
        for table in data_browser_service.list_tables()
    ]


@router.get("/{table}", response_model=DataListResponse)
async def list_records(
    table: str,
    _: Annotated[Any, Depends(require_control_panel)],
    page: int = 1,
    page_size: int = 20,
    search: str = "",
) -> DataListResponse:
    """List records for one internal table."""
    try:
        result = await data_browser_service.list_records(
            table,
            page=page,
            page_size=page_size,
            search=search,
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return DataListResponse(
        table=result.table,
        primary_key=result.primary_key,
        columns=result.columns,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        search=search.strip(),
        items=result.items,
    )


@router.get("/{table}/{record_id}", response_model=DataRecordResponse)
async def get_record(
    table: str,
    record_id: str,
    _: Annotated[Any, Depends(require_control_panel)],
) -> DataRecordResponse:
    """Fetch one record from a browsable internal table."""
    try:
        result = await data_browser_service.get_record(table, record_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return DataRecordResponse(
        table=result.table,
        primary_key=result.primary_key,
        record=result.record,
    )
