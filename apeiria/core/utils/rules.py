"""NoneBot2 Rule factories for permission checks."""

from nonebot.adapters import Bot, Event
from nonebot.rule import Rule


def admin_check(level: int = 5) -> Rule:
    """Rule that requires minimum permission level."""

    async def _check(bot: Bot, event: Event) -> bool:
        from apeiria.core.utils.permission import check_permission, extract_group_id

        try:
            user_id = event.get_user_id()
        except Exception:  # noqa: BLE001
            return False

        from nonebot import get_driver

        if user_id in get_driver().config.superusers:
            return True

        session_id = event.get_session_id()
        group_id = extract_group_id(session_id, user_id)
        if not group_id:
            return False

        adapter_level = await _get_adapter_role_level(bot, event, group_id)
        if adapter_level >= level:
            return True

        return await check_permission(user_id, group_id, level)

    return Rule(_check)


def ensure_group() -> Rule:
    """Rule that only passes in group context."""

    async def _check(event: Event) -> bool:
        try:
            user_id = event.get_user_id()
        except Exception:  # noqa: BLE001
            return False
        return event.get_session_id() != user_id

    return Rule(_check)


def ensure_private() -> Rule:
    """Rule that only passes in private (DM) context."""

    async def _check(event: Event) -> bool:
        try:
            user_id = event.get_user_id()
        except Exception:  # noqa: BLE001
            return False
        return event.get_session_id() == user_id

    return Rule(_check)

async def _get_adapter_role_level(bot: Bot, event: Event, group_id: str) -> int:
    """Detect adapter-level roles. Returns 6=owner, 5=admin, 0=other."""
    try:
        user_id = event.get_user_id()
        info = await bot.call_api(
            "get_group_member_info",
            group_id=int(group_id),
            user_id=int(user_id),
        )
        role = info.get("role", "")
        if role == "owner":
            return 6
        if role == "admin":
            return 5
    except Exception:  # noqa: BLE001
        pass
    return 0
