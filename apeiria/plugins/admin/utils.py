"""Common utilities for admin plugin."""

from __future__ import annotations

import nonebot
from nonebot.adapters import Event  # noqa: TC002

from apeiria.core.i18n import t
from apeiria.domains.permissions import permission_service


def extract_group_id(event: Event) -> str | None:
    """Extract group_id from event session."""
    try:
        user_id = event.get_user_id()
    except Exception:  # noqa: BLE001
        return None
    return permission_service.extract_group_id(event.get_session_id(), user_id)


def resolve_target_id(target: object) -> str:
    """Resolve user target (At mention or string) to user_id string."""
    from nonebot_plugin_alconna import At

    if isinstance(target, At):
        return str(target.target)
    return str(target)


def is_superuser(user_id: str) -> bool:
    """Check if user_id is a superuser."""
    return user_id in nonebot.get_driver().config.superusers


def validate_target(caller_id: str, target_id: str, action: str) -> str | None:
    """Validate target for admin actions. Returns error message or None."""
    if target_id == caller_id:
        return t("admin.validate.self_action", action=action)
    if is_superuser(target_id):
        return t("admin.validate.superuser_action", action=action)
    return None
