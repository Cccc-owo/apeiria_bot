"""Ban/unban commands."""

from arclet.alconna import Args
from nonebot.adapters import Event
from nonebot_plugin_alconna import Alconna, At, Match, Option, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.rules import admin_check, ensure_group

from .utils import resolve_target_id, validate_target

_ban = on_alconna(
    Alconna(
        "ban",
        Args["user", [str, At]],
        Option("-t|--time", Args["duration", int]),
        Option("-r|--reason", Args["reason", str]),
    ),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)

_unban = on_alconna(
    Alconna("unban", Args["user", [str, At]]),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)


@_ban.handle()
async def handle_ban(
    event: Event,
    user: Match[str | At],
    duration: Match[int],
    reason: Match[str],
) -> None:
    caller_id = event.get_user_id()
    target_id = resolve_target_id(user.result)

    if err := validate_target(caller_id, target_id, "封禁"):
        await _ban.finish(err)

    dur = duration.result * 60 if duration.available else 0
    if duration.available and duration.result < 0:
        await _ban.finish(t("admin.ban.negative_duration"))
    ban_reason = reason.result if reason.available else None

    from datetime import datetime, timezone

    from nonebot_plugin_orm import get_session

    from apeiria.core.models.ban import BanConsole
    from apeiria.core.utils.permission import invalidate_ban_cache

    async with get_session() as session:
        session.add(
            BanConsole(
                user_id=target_id,
                group_id=None,
                ban_time=datetime.now(timezone.utc),
                duration=dur,
                reason=ban_reason,
            )
        )
        await session.commit()

    await invalidate_ban_cache(target_id)

    from apeiria.core.utils.helpers import format_duration

    dur_text = format_duration(dur)
    if ban_reason:
        msg = t(
            "admin.ban.success_reason",
            target=target_id,
            duration=dur_text,
            reason=ban_reason,
        )
    else:
        msg = t("admin.ban.success", target=target_id, duration=dur_text)
    await _ban.finish(msg)


@_unban.handle()
async def handle_unban(user: Match[str | At]) -> None:
    target_id = resolve_target_id(user.result)

    from nonebot_plugin_orm import get_session
    from sqlalchemy import delete, select

    from apeiria.core.models.ban import BanConsole
    from apeiria.core.utils.permission import invalidate_ban_cache

    async with get_session() as session:
        result = await session.execute(
            select(BanConsole).where(BanConsole.user_id == target_id).limit(1)
        )
        if not result.scalar_one_or_none():
            await _unban.finish(t("admin.ban.not_banned", target=target_id))

        await session.execute(delete(BanConsole).where(BanConsole.user_id == target_id))
        await session.commit()

    await invalidate_ban_cache(target_id)
    await _unban.finish(t("admin.ban.unbanned", target=target_id))
