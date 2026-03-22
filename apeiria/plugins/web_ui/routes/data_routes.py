"""Generic data browser routes."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from apeiria.core.i18n import t
from apeiria.plugins.web_ui.auth import require_auth
from apeiria.plugins.web_ui.models import (
    DataListResponse,
    DataRecordResponse,
    DataTableInfo,
    DataUpdateRequest,
)

router = APIRouter()


def _table_registry() -> dict[str, tuple[type[Any], str]]:
    from apeiria.core.models import (
        BanConsole,
        CommandStatistics,
        GroupConsole,
        LevelUser,
        PluginInfo,
        UserConsole,
    )

    return {
        "users": (UserConsole, t("web_ui.data.table_users")),
        "groups": (GroupConsole, t("web_ui.data.table_groups")),
        "levels": (LevelUser, t("web_ui.data.table_levels")),
        "bans": (BanConsole, t("web_ui.data.table_bans")),
        "plugins": (PluginInfo, t("web_ui.data.table_plugins")),
        "statistics": (CommandStatistics, t("web_ui.data.table_statistics")),
    }


def _resolve_table(table: str) -> tuple[type[Any], str]:
    registry = _table_registry()
    result = registry.get(table)
    if not result:
        raise HTTPException(status_code=404, detail=t("web_ui.data.table_not_found"))
    return result


def _serialize_value(value: object | None) -> object | None:
    if value is None:
        return None
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _serialize_record(model: type[Any], record: Any) -> dict[str, object | None]:
    return {
        column.key: _serialize_value(getattr(record, column.key))
        for column in model.__table__.columns
    }


def _primary_key_name(model: type[Any]) -> str:
    return next(iter(model.__table__.primary_key.columns)).key


def _editable_columns(model: type[Any]) -> set[str]:
    primary_key = _primary_key_name(model)
    protected = {primary_key, "created_at", "updated_at"}
    return {
        column.key
        for column in model.__table__.columns
        if column.key not in protected
    }


@router.get("/", response_model=list[DataTableInfo])
async def list_tables(_: Annotated[Any, Depends(require_auth)]) -> list[DataTableInfo]:
    tables: list[DataTableInfo] = []
    for name, (model, label) in _table_registry().items():
        tables.append(
            DataTableInfo(
                name=name,
                label=label,
                primary_key=_primary_key_name(model),
            )
        )
    return tables


@router.get("/{table}", response_model=DataListResponse)
async def list_records(
    table: str,
    _: Annotated[Any, Depends(require_auth)],
    page: int = 1,
    page_size: int = 20,
) -> DataListResponse:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import func, select

    model, _ = _resolve_table(table)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    async with get_session() as session:
        total_stmt = select(func.count()).select_from(model)
        total = await session.scalar(total_stmt) or 0

        stmt = (
            select(model)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

    return DataListResponse(
        table=table,
        primary_key=_primary_key_name(model),
        columns=[column.key for column in model.__table__.columns],
        total=total,
        page=page,
        page_size=page_size,
        items=[_serialize_record(model, row) for row in rows],
    )


@router.get("/{table}/{record_id}", response_model=DataRecordResponse)
async def get_record(
    table: str,
    record_id: str,
    _: Annotated[Any, Depends(require_auth)],
) -> DataRecordResponse:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    model, _ = _resolve_table(table)
    primary_key = _primary_key_name(model)
    column = getattr(model, primary_key)

    async with get_session() as session:
        result = await session.execute(select(model).where(column == record_id))
        record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail=t("web_ui.data.record_not_found"))

    return DataRecordResponse(
        table=table,
        primary_key=primary_key,
        record=_serialize_record(model, record),
    )


@router.patch("/{table}/{record_id}", response_model=DataRecordResponse)
async def update_record(
    table: str,
    record_id: str,
    body: DataUpdateRequest,
    _: Annotated[Any, Depends(require_auth)],
) -> DataRecordResponse:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    model, _ = _resolve_table(table)
    primary_key = _primary_key_name(model)
    column = getattr(model, primary_key)
    editable = _editable_columns(model)

    invalid_keys = sorted(set(body.values) - editable)
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=t(
                "web_ui.data.fields_not_editable",
                fields=", ".join(invalid_keys),
            ),
        )

    async with get_session() as session:
        result = await session.execute(select(model).where(column == record_id))
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=404,
                detail=t("web_ui.data.record_not_found"),
            )

        for key, value in body.values.items():
            setattr(record, key, value)

        await session.commit()
        await session.refresh(record)

    return DataRecordResponse(
        table=table,
        primary_key=primary_key,
        record=_serialize_record(model, record),
    )
