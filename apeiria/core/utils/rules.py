"""NoneBot2 Rule factories for permission checks."""

from contextlib import suppress

from nonebot import get_driver
from nonebot.adapters import Bot, Event
from nonebot.rule import Rule

from apeiria.core.i18n import t
from apeiria.domains.permissions import permission_service


def owner_check() -> Rule:
    """Rule that requires the current user to be a configured superuser."""

    async def _check(bot: Bot, event: Event) -> bool:
        try:
            user_id = event.get_user_id()
        except Exception:  # noqa: BLE001
            return False

        superusers = getattr(get_driver().config, "superusers", set())
        if str(user_id) in {str(item) for item in superusers}:
            return True

        with suppress(Exception):
            await bot.send(event, t("admin.owner_only"))
        return False

    return Rule(_check)


def admin_check(level: int = 5) -> Rule:
    """Rule that requires minimum permission level."""

    async def _check(bot: Bot, event: Event) -> bool:
        context = await permission_service.build_context(bot, event)
        if context is None:
            return False

        if context.user_id in get_driver().config.superusers:
            return True

        if context.group_id is None:
            return False

        if context.adapter_role_level >= level:
            return True

        return await permission_service.check_permission(
            context.user_id,
            context.group_id,
            level,
        )

    return Rule(_check)


def ensure_group() -> Rule:
    """Rule that only passes in group context."""

    async def _check(event: Event) -> bool:
        try:
            user_id = event.get_user_id()
        except Exception:  # noqa: BLE001
            return False
        return (
            permission_service.extract_group_id(event.get_session_id(), user_id)
            is not None
        )

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
    return await permission_service.get_adapter_role_level(bot, event, group_id)
