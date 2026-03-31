"""Read-only data browser application services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from apeiria.shared.exceptions import ResourceNotFoundError
from apeiria.shared.i18n import t


@dataclass(frozen=True)
class DataTableDefinition:
    """Read-only table metadata."""

    name: str
    label: str
    model: type[Any]
    primary_key: str


@dataclass(frozen=True)
class DataListResult:
    """Read-only table page response."""

    table: str
    primary_key: str
    columns: list[str]
    total: int
    page: int
    page_size: int
    items: list[dict[str, object | None]]


@dataclass(frozen=True)
class DataRecordResult:
    """Read-only record response."""

    table: str
    primary_key: str
    record: dict[str, object | None]


class DataBrowserService:
    """Provide read-only browsing over selected internal tables."""

    def list_tables(self) -> list[DataTableDefinition]:
        return list(self._table_registry().values())

    async def list_records(
        self,
        table: str,
        *,
        page: int,
        page_size: int,
        search: str = "",
    ) -> DataListResult:
        """List records for a table with optional global text search."""
        from nonebot_plugin_orm import get_session
        from sqlalchemy import String, cast, func, or_, select

        definition = self._resolve_table(table)
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 100))
        normalized_search = search.strip()
        search_filter = None
        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                *[
                    cast(getattr(definition.model, column.key), String).ilike(pattern)
                    for column in definition.model.__table__.columns
                ]
            )

        async with get_session() as session:
            total_stmt = select(func.count()).select_from(definition.model)
            if search_filter is not None:
                total_stmt = total_stmt.where(search_filter)
            total = await session.scalar(total_stmt) or 0

            stmt = select(definition.model)
            if search_filter is not None:
                stmt = stmt.where(search_filter)
            stmt = stmt.offset((safe_page - 1) * safe_page_size).limit(safe_page_size)
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return DataListResult(
            table=definition.name,
            primary_key=definition.primary_key,
            columns=[column.key for column in definition.model.__table__.columns],
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            items=[self._serialize_record(definition.model, row) for row in rows],
        )

    async def get_record(self, table: str, record_id: str) -> DataRecordResult:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        definition = self._resolve_table(table)
        column = getattr(definition.model, definition.primary_key)

        async with get_session() as session:
            result = await session.execute(
                select(definition.model).where(column == record_id)
            )
            record = result.scalar_one_or_none()

        if record is None:
            raise ResourceNotFoundError(t("web_ui.data.record_not_found"))

        return DataRecordResult(
            table=definition.name,
            primary_key=definition.primary_key,
            record=self._serialize_record(definition.model, record),
        )

    def _table_registry(self) -> dict[str, DataTableDefinition]:
        from apeiria.infra.db.models import (
            AccessPolicyEntry,
            CommandStatistics,
            GroupConsole,
            LevelUser,
            PluginInfo,
            PluginPolicyEntry,
            UserConsole,
        )

        models = {
            "users": (UserConsole, t("web_ui.data.table_users")),
            "groups": (GroupConsole, t("web_ui.data.table_groups")),
            "levels": (LevelUser, t("web_ui.data.table_levels")),
            "access_rules": (AccessPolicyEntry, t("web_ui.data.table_access_rules")),
            "plugins": (PluginInfo, t("web_ui.data.table_plugins")),
            "plugin_policies": (
                PluginPolicyEntry,
                t("web_ui.data.table_plugin_policies"),
            ),
            "statistics": (CommandStatistics, t("web_ui.data.table_statistics")),
        }
        return {
            name: DataTableDefinition(
                name=name,
                label=label,
                model=model,
                primary_key=self._primary_key_name(model),
            )
            for name, (model, label) in models.items()
        }

    def _resolve_table(self, table: str) -> DataTableDefinition:
        definition = self._table_registry().get(table)
        if definition is None:
            raise ResourceNotFoundError(t("web_ui.data.table_not_found"))
        return definition

    def _primary_key_name(self, model: type[Any]) -> str:
        return next(iter(model.__table__.primary_key.columns)).key

    def _serialize_record(
        self,
        model: type[Any],
        record: Any,
    ) -> dict[str, object | None]:
        return {
            column.key: self._serialize_value(getattr(record, column.key))
            for column in model.__table__.columns
        }

    def _serialize_value(self, value: object | None) -> object | None:
        if value is None:
            return None
        if isinstance(value, datetime | date | time):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value


data_browser_service = DataBrowserService()
