"""Kick command — remove user from group via adapter API."""

from arclet.alconna import Args
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import Alconna, At, Match, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.rules import admin_check, ensure_group

from .utils import extract_group_id, resolve_target_id, validate_target

_kick = on_alconna(
    Alconna("kick", Args["user", [str, At]]),
    use_cmd_start=True,
    rule=admin_check(6) & ensure_group(),
    priority=5,
    block=True,
)


@_kick.handle()
async def handle_kick(bot: Bot, event: Event, user: Match[str | At]) -> None:
    caller_id = event.get_user_id()
    target_id = resolve_target_id(user.result)

    if err := validate_target(caller_id, target_id, "踢出"):
        await _kick.finish(err)

    group_id = extract_group_id(event)
    if not group_id:
        await _kick.finish(t("common.group_only"))

    try:
        await bot.call_api(
            "set_group_kick",
            group_id=int(group_id),
            user_id=int(target_id),
            reject_add_request=False,
        )
        await _kick.finish(t("admin.kick.success", target=target_id))
    except Exception:  # noqa: BLE001
        await _kick.finish(t("admin.kick.failed"))
