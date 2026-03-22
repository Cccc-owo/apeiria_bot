"""Mute/unmute commands — group-level mute via adapter API."""

from arclet.alconna import Args
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import Alconna, At, Match, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import format_duration
from apeiria.core.utils.rules import admin_check, ensure_group

from .utils import extract_group_id, resolve_target_id, validate_target

_mute = on_alconna(
    Alconna("mute", Args["user", [str, At]], Args["duration", int]),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)

_unmute = on_alconna(
    Alconna("unmute", Args["user", [str, At]]),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)


@_mute.handle()
async def handle_mute(
    bot: Bot, event: Event, user: Match[str | At], duration: Match[int]
) -> None:
    caller_id = event.get_user_id()
    target_id = resolve_target_id(user.result)

    if err := validate_target(caller_id, target_id, "禁言"):
        await _mute.finish(err)

    if duration.result <= 0:
        await _mute.finish(t("admin.mute.zero_duration"))

    dur_seconds = duration.result * 60
    group_id = extract_group_id(event)
    if not group_id:
        await _mute.finish(t("common.group_only"))

    try:
        await bot.call_api(
            "set_group_ban",
            group_id=int(group_id),
            user_id=int(target_id),
            duration=dur_seconds,
        )
        dur_text = format_duration(dur_seconds)
        await _mute.finish(t("admin.mute.success", target=target_id, duration=dur_text))
    except Exception:  # noqa: BLE001
        await _mute.finish(t("admin.mute.failed"))


@_unmute.handle()
async def handle_unmute(bot: Bot, event: Event, user: Match[str | At]) -> None:
    target_id = resolve_target_id(user.result)
    group_id = extract_group_id(event)
    if not group_id:
        await _unmute.finish(t("common.group_only"))

    try:
        await bot.call_api(
            "set_group_ban",
            group_id=int(group_id),
            user_id=int(target_id),
            duration=0,
        )
        await _unmute.finish(t("admin.mute.unmuted", target=target_id))
    except Exception:  # noqa: BLE001
        await _unmute.finish(t("admin.mute.unmute_failed"))
