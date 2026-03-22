"""Ban list command — view active bans."""

from nonebot_plugin_alconna import Alconna, on_alconna

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import format_duration
from apeiria.core.utils.rules import admin_check, ensure_group

_banlist = on_alconna(
    Alconna("banlist"),
    use_cmd_start=True,
    rule=admin_check(5) & ensure_group(),
    priority=5,
    block=True,
)


@_banlist.handle()
async def handle_banlist() -> None:
    from datetime import datetime, timezone

    from nonebot_plugin_orm import get_session
    from sqlalchemy import select

    from apeiria.core.models.ban import BanConsole

    async with get_session() as session:
        result = await session.execute(select(BanConsole))
        bans = result.scalars().all()

    if not bans:
        await _banlist.finish(t("admin.banlist.empty"))

    now = datetime.now(timezone.utc)
    lines = [t("admin.banlist.title"), ""]
    for ban in bans:
        user = ban.user_id or "?"

        if ban.duration == 0:
            dur = format_duration(0)
        elif ban.ban_time:
            bt = ban.ban_time
            if bt.tzinfo is None:
                bt = bt.replace(tzinfo=timezone.utc)
            remaining = ban.duration - int((now - bt).total_seconds())
            dur = format_duration(max(remaining, 0)) if remaining > 0 else "expired"
        else:
            dur = format_duration(ban.duration)

        reason = ban.reason or t("admin.banlist.no_reason")
        lines.append(t("admin.banlist.item", user=user, duration=dur, reason=reason))

    await _banlist.finish("\n".join(lines))
