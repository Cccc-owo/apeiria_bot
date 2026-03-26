"""Plugin enable/disable commands per group."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from arclet.alconna import Args
from nonebot.adapters import Event  # noqa: TC002
from nonebot_plugin_alconna import Alconna, Match, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import (
    find_loaded_plugin,
    get_plugin_name,
    get_plugin_protection_reason,
)
from apeiria.core.utils.rules import admin_check, ensure_group

from .utils import extract_group_id

if TYPE_CHECKING:
    from nonebot.plugin import Plugin

_enable = on_alconna(
    Alconna("enable", Args["plugin_name", str]),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)

_disable = on_alconna(
    Alconna("disable", Args["plugin_name", str]),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)


@_enable.handle()
async def handle_enable(event: Event, plugin_name: Match[str]) -> None:
    name = plugin_name.result
    group_id = extract_group_id(event)
    if not group_id:
        await _enable.finish(t("common.group_only"))
    plugin = find_loaded_plugin(name)
    if not plugin:
        await _enable.finish(t("common.plugin_not_found", name=name))
    await _toggle_plugin(group_id, plugin.module_name, enable=True)
    await _enable.finish(t("admin.plugin.enabled", name=get_plugin_name(plugin)))


@_disable.handle()
async def handle_disable(event: Event, plugin_name: Match[str]) -> None:
    name = plugin_name.result
    group_id = extract_group_id(event)
    if not group_id:
        await _disable.finish(t("common.group_only"))
    plugin = find_loaded_plugin(name)
    if not plugin:
        await _disable.finish(t("common.plugin_not_found", name=name))
    reason = get_plugin_protection_reason(plugin.module_name)
    if reason:
        await _disable.finish(t("admin.plugin.protected", name=get_plugin_name(plugin)))
    await _toggle_plugin(group_id, plugin.module_name, enable=False)
    await _disable.finish(t("admin.plugin.disabled", name=get_plugin_name(plugin)))


def _find_plugin(name: str) -> Plugin | None:
    """Backward-compatible plugin resolver."""
    return find_loaded_plugin(name)


async def _toggle_plugin(group_id: str, plugin_name: str, *, enable: bool) -> None:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole
    from apeiria.core.utils.permission import invalidate_group_plugin_cache

    async with get_session() as session:
        result = await session.execute(
            select(GroupConsole).where(GroupConsole.group_id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            group = GroupConsole(group_id=group_id, disabled_plugins="[]")
            session.add(group)

        try:
            disabled: list[str] = json.loads(group.disabled_plugins or "[]")
        except (json.JSONDecodeError, TypeError):
            disabled = []

        if enable:
            disabled = [p for p in disabled if p != plugin_name]
        elif plugin_name not in disabled:
            disabled.append(plugin_name)

        group.disabled_plugins = json.dumps(disabled)
        await session.commit()

    await invalidate_group_plugin_cache(group_id)
