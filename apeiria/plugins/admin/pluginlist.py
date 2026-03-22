"""Plugin list command — view plugin enable/disable status in current group."""

import json

import nonebot
from nonebot.adapters import Event
from nonebot_plugin_alconna import Alconna, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import get_plugin_name, is_plugin_protected
from apeiria.core.utils.rules import admin_check, ensure_group

from .utils import extract_group_id

_pluginlist = on_alconna(
    Alconna("pluginlist"),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)


@_pluginlist.handle()
async def handle_pluginlist(event: Event) -> None:
    group_id = extract_group_id(event)
    if not group_id:
        await _pluginlist.finish(t("common.group_only"))

    # Get disabled plugins for this group
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole

    async with get_session() as session:
        result = await session.execute(
            select(GroupConsole.disabled_plugins).where(
                GroupConsole.group_id == group_id
            )
        )
        raw = result.scalar_one_or_none()

    try:
        disabled: list[str] = json.loads(raw) if raw else []
    except (json.JSONDecodeError, TypeError):
        disabled = []

    # Build list from loaded plugins (skip hidden/internal)
    from apeiria.core.configs.models import PluginType
    from apeiria.core.utils.helpers import get_plugin_extra

    lines = [t("admin.pluginlist.title"), ""]
    plugins = sorted(nonebot.get_loaded_plugins(), key=get_plugin_name)
    for plugin in plugins:
        extra = get_plugin_extra(plugin)
        if extra and extra.plugin_type in (PluginType.HIDDEN, PluginType.PARENT):
            continue
        if not plugin.metadata:
            continue

        name = get_plugin_name(plugin)
        is_disabled = plugin.module_name in disabled
        if is_plugin_protected(plugin.module_name):
            lines.append(t("admin.pluginlist.item_locked", name=name))
        elif is_disabled:
            lines.append(t("admin.pluginlist.item_off", name=name))
        else:
            lines.append(t("admin.pluginlist.item_on", name=name))

    await _pluginlist.finish("\n".join(lines))
