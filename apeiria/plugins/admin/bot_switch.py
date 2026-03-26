"""Bot on/off commands — enable or disable bot in current group."""

from nonebot.adapters import Event
from nonebot_plugin_alconna import Alconna, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.rules import admin_check, ensure_group

from .utils import extract_group_id

_boton = on_alconna(
    Alconna("boton"),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)

_botoff = on_alconna(
    Alconna("botoff"),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)


@_boton.handle()
async def handle_boton(event: Event) -> None:
    group_id = extract_group_id(event)
    if not group_id:
        await _boton.finish(t("common.group_only"))
    await _set_bot_status(group_id, status=True)
    await _boton.finish(t("admin.bot.on"))


@_botoff.handle()
async def handle_botoff(event: Event) -> None:
    group_id = extract_group_id(event)
    if not group_id:
        await _botoff.finish(t("common.group_only"))
    await _set_bot_status(group_id, status=False)
    await _botoff.finish(t("admin.bot.off"))


async def _set_bot_status(group_id: str, *, status: bool) -> None:
    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.group import GroupConsole
    from apeiria.core.utils.permission import invalidate_group_bot_status_cache

    async with get_session() as session:
        result = await session.execute(
            select(GroupConsole).where(GroupConsole.group_id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            group = GroupConsole(group_id=group_id, bot_status=status)
            session.add(group)
        else:
            group.bot_status = status
        await session.commit()
    await invalidate_group_bot_status_cache(group_id)
