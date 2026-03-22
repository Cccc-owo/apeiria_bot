"""Set user permission level command."""

from arclet.alconna import Args
from nonebot.adapters import Event
from nonebot_plugin_alconna import Alconna, At, Match, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.rules import admin_check, ensure_group

from .utils import extract_group_id, is_superuser, resolve_target_id

_setlevel = on_alconna(
    Alconna("setlevel", Args["user", [str, At]], Args["level", int]),
    use_cmd_start=True,
    rule=admin_check(6) & ensure_group(),
    priority=5,
    block=True,
)


@_setlevel.handle()
async def handle_setlevel(
    event: Event,
    user: Match[str | At],
    level: Match[int],
) -> None:
    caller_id = event.get_user_id()
    target_id = resolve_target_id(user.result)
    target_level = level.result

    if target_id == caller_id:
        await _setlevel.finish(t("admin.level.self_modify"))

    if is_superuser(target_id):
        await _setlevel.finish(t("admin.level.superuser_modify"))

    if not 0 <= target_level <= 4:  # noqa: PLR2004
        await _setlevel.finish(t("admin.level.range_error"))

    group_id = extract_group_id(event)
    if not group_id:
        await _setlevel.finish(t("common.group_only"))

    from apeiria.core.utils.permission import get_user_level, set_user_level

    old_level = await get_user_level(target_id, group_id)
    await set_user_level(target_id, group_id, target_level)
    await _setlevel.finish(
        t("admin.level.updated", target=target_id, old=old_level, new=target_level)
    )
