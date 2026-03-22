"""Help command handler."""

from arclet.alconna import Args
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import Alconna, Match, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage

from apeiria.core.i18n import t

_help = on_alconna(
    Alconna("help", Args["plugin_name?", str]),
    use_cmd_start=True,
    priority=1,
    block=True,
)


def _is_console(bot: Bot) -> bool:
    """Check if current adapter is Console (text-only)."""
    return bot.adapter.get_name() == "Console"


@_help.handle()
async def handle_help(bot: Bot, event: Event, plugin_name: Match[str]) -> None:
    if plugin_name.available:
        await _show_plugin_detail(bot, plugin_name.result)
    else:
        await _show_help_list(bot, event)


async def _show_help_list(bot: Bot, event: Event) -> None:
    from .generator import generate_help_list

    try:
        user_id = event.get_user_id()
    except Exception:  # noqa: BLE001
        user_id = ""

    session_id = event.get_session_id()
    group_id: str | None = None
    if session_id != user_id and "_" in session_id:
        parts = session_id.split("_")
        if len(parts) >= 2:  # noqa: PLR2004
            group_id = parts[1] if parts[0] == "group" else parts[0]

    plugins = generate_help_list(user_id, group_id)

    if _is_console(bot):
        lines = [t("help.list_title"), ""]
        for p in plugins:
            cmds = " ".join(f"/{c}" for c in p.commands) if p.commands else ""
            level = f" [Lv.{p.admin_level}]" if p.admin_level > 0 else ""
            lines.append(f"【{p.name}】{level} {p.description}")
            if cmds:
                lines.append(f"  {t('help.commands_label')}: {cmds}")
        lines.append("")
        lines.append(t("help.list_footer"))
        await _help.finish("\n".join(lines))

    from .renderer import render_help_list

    img_bytes = await render_help_list(plugins)
    await UniMessage.image(raw=img_bytes).send()


async def _show_plugin_detail(bot: Bot, name: str) -> None:
    from .generator import find_plugin_by_name

    plugin_info = find_plugin_by_name(name)
    if not plugin_info:
        await _help.finish(t("help.not_found", name=name))

    if _is_console(bot):
        cmds = (
            " ".join(f"/{c}" for c in plugin_info.commands)
            if plugin_info.commands
            else t("help.no_commands")
        )
        lines = [
            f"【{plugin_info.name}】 v{plugin_info.version}",
            f"{t('help.detail_type')}: {plugin_info.plugin_type} | "
            f"{t('help.detail_permission')}: Lv.{plugin_info.admin_level}",
            f"{t('help.detail_description')}: "
            f"{plugin_info.description or t('help.no_description')}",
            f"{t('help.commands_label')}: {cmds}",
            "",
            plugin_info.usage or t("help.no_usage"),
        ]
        await _help.finish("\n".join(lines))

    from .renderer import render_plugin_detail

    img_bytes = await render_plugin_detail(plugin_info)
    await UniMessage.image(raw=img_bytes).send()
