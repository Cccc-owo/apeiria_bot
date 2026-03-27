"""Runtime gateways for permission-related feedback."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from apeiria.domains.permissions.context import (
    is_onebot_api_available,
    map_role_to_level,
    to_onebot_numeric_id,
)

if TYPE_CHECKING:
    from nonebot.adapters import Bot, Event


class PermissionFeedbackGateway:
    """Own best-effort user feedback for ignored permission actions."""

    async def send_ignored_message(
        self,
        bot: Bot,
        event: Event,
        message: str,
    ) -> None:
        with contextlib.suppress(Exception):
            await bot.send(event, message)


class PermissionRuntimeGateway:
    """Own adapter/runtime-specific permission lookups."""

    async def get_adapter_role_level(
        self,
        bot: Bot,
        event: Event,
        *,
        group_id: str,
    ) -> int:
        """Resolve adapter role level through runtime-specific APIs."""
        if not is_onebot_api_available(bot):
            return 0

        try:
            user_id = event.get_user_id()
            api_group_id = to_onebot_numeric_id(group_id)
            api_user_id = to_onebot_numeric_id(user_id)
            if api_group_id is None or api_user_id is None:
                return 0

            info = await bot.call_api(
                "get_group_member_info",
                group_id=api_group_id,
                user_id=api_user_id,
            )
            return map_role_to_level(info.get("role"))
        except Exception:  # noqa: BLE001
            return 0


permission_feedback_gateway = PermissionFeedbackGateway()
permission_runtime_gateway = PermissionRuntimeGateway()
