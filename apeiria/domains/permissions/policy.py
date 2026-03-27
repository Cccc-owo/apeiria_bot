"""Pure policy helpers for permission decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apeiria.domains.permissions.service import PermissionContext


def is_ban_active(bans: list[object], *, now: datetime | None = None) -> bool:
    """Return whether any ban in the list is currently active."""
    current_time = now or datetime.now(timezone.utc)
    for ban in bans:
        duration = getattr(ban, "duration", 0)
        if duration == 0:
            return True

        ban_time = getattr(ban, "ban_time", None)
        if ban_time is None or duration <= 0:
            continue
        if ban_time.tzinfo is None:
            ban_time = ban_time.replace(tzinfo=timezone.utc)
        if (current_time - ban_time).total_seconds() < duration:
            return True
    return False


def can_run_with_level(
    context: "PermissionContext",
    *,
    required_level: int,
    db_level: int,
) -> bool:
    """Return whether the context satisfies the required level."""
    if required_level <= 0 or context.group_id is None:
        return True
    effective_level = max(context.adapter_role_level, db_level)
    return effective_level >= required_level


def effective_permission_level(
    context: "PermissionContext",
    *,
    db_level: int,
) -> int:
    """Return the effective level combining adapter and persisted state."""
    return max(context.adapter_role_level, db_level)


def level_display_name(required_level: int, *, admin_name: str, owner_name: str) -> str:
    """Return a display label for one permission level."""
    level_names = {5: admin_name, 6: owner_name}
    return level_names.get(required_level, f"Lv.{required_level}")
