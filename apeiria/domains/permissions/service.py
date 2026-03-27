"""Permission domain services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import nonebot
from nonebot.exception import IgnoredException
from nonebot.log import logger

from apeiria.core.i18n import t
from apeiria.core.utils.helpers import get_plugin_extra, is_plugin_protected
from apeiria.domains.permissions.cache import permission_cache
from apeiria.domains.permissions.context import (
    ConversationType,
    extract_group_id,
    get_event_role_level,
    group_id_from_event,
    resolve_conversation_type,
)
from apeiria.domains.permissions.gateway import (
    permission_feedback_gateway,
    permission_runtime_gateway,
)
from apeiria.domains.permissions.policy import (
    can_run_with_level,
    effective_permission_level,
    is_ban_active,
    level_display_name,
)
from apeiria.domains.permissions.repository import permission_state_repository

if TYPE_CHECKING:
    from nonebot.adapters import Bot, Event


@dataclass(frozen=True)
class PermissionContext:
    """Normalized permission context derived from a bot event."""

    user_id: str
    conversation_type: ConversationType
    group_id: str | None = None
    adapter_role_level: int = 0


class PermissionService:
    """Central permission service for hooks, rules, and management APIs."""

    def extract_group_id(self, session_id: str, user_id: str) -> str | None:
        """Extract a group identifier from a session id when adapter data is absent."""
        return extract_group_id(session_id, user_id)

    async def build_context(self, bot: Bot, event: Event) -> PermissionContext | None:
        """Build a normalized permission context from an abstract event."""
        try:
            user_id = event.get_user_id()
        except Exception:  # noqa: BLE001
            return None

        group_id = group_id_from_event(event)
        conversation_type = resolve_conversation_type(event, user_id, group_id)

        adapter_role_level = (
            await self.get_adapter_role_level(bot, event, group_id)
            if group_id is not None
            else 0
        )
        return PermissionContext(
            user_id=user_id,
            conversation_type=conversation_type,
            group_id=group_id,
            adapter_role_level=adapter_role_level,
        )

    async def get_adapter_role_level(
        self,
        bot: Bot,
        event: Event,
        group_id: str | None,
    ) -> int:
        """Detect adapter-level roles. Returns 6=owner, 5=admin, 0=other."""
        if group_id is None:
            return 0

        event_level = get_event_role_level(event)
        if event_level > 0:
            return event_level

        return await permission_runtime_gateway.get_adapter_role_level(
            bot,
            event,
            group_id=group_id,
        )

    async def invalidate_user_level_cache(self, user_id: str, group_id: str) -> None:
        await permission_cache.invalidate_user_level(user_id, group_id)

    async def invalidate_ban_cache(
        self,
        user_id: str,
        group_id: str | None = None,
    ) -> None:
        await permission_cache.invalidate_ban(user_id, group_id)

    async def invalidate_group_plugin_cache(self, group_id: str) -> None:
        await permission_cache.invalidate_group_disabled_plugins(group_id)

    async def invalidate_group_bot_status_cache(self, group_id: str) -> None:
        await permission_cache.invalidate_group_bot_enabled(group_id)

    async def invalidate_plugin_global_cache(self, plugin_module: str) -> None:
        await permission_cache.invalidate_plugin_global_enabled(plugin_module)

    async def get_user_level(self, user_id: str, group_id: str) -> int:
        cached = await permission_cache.get_user_level(user_id, group_id)
        if cached is not None:
            return cached

        level = await permission_state_repository.get_user_level(user_id, group_id)
        await permission_cache.set_user_level(user_id, group_id, level)
        return level

    async def list_user_levels(self) -> list[tuple[str, str, int]]:
        return await permission_state_repository.list_user_levels()

    async def set_user_level(self, user_id: str, group_id: str, level: int) -> None:
        await permission_state_repository.set_user_level(user_id, group_id, level)
        await self.invalidate_user_level_cache(user_id, group_id)
        logger.debug("Set level {}:{} -> {}", user_id, group_id, level)

    async def is_banned(self, user_id: str, group_id: str | None = None) -> bool:
        cached = await permission_cache.get_ban(user_id, group_id)
        if cached is not None:
            return cached

        bans = await permission_state_repository.list_active_ban_candidates(
            user_id,
            group_id,
        )

        banned = is_ban_active(bans)
        await permission_cache.set_ban(user_id, group_id, banned=banned)
        return banned

    async def list_bans(
        self,
    ) -> list[tuple[int, str | None, str | None, int, str | None]]:
        return await permission_state_repository.list_bans()

    async def create_ban(
        self,
        *,
        user_id: str,
        group_id: str | None,
        duration: int,
        reason: str | None,
    ) -> tuple[int, str | None, str | None, int, str | None]:
        record = await permission_state_repository.create_ban(
            user_id=user_id,
            group_id=group_id,
            duration=duration,
            reason=reason,
        )
        await self.invalidate_ban_cache(user_id, group_id)
        return record

    async def delete_ban(self, ban_id: int) -> tuple[str | None, str | None]:
        from apeiria.domains.exceptions import ResourceNotFoundError

        try:
            user_id, group_id = await permission_state_repository.delete_ban(ban_id)
        except ResourceNotFoundError:
            raise ResourceNotFoundError(t("web_ui.permissions.ban_not_found")) from None

        if user_id:
            await self.invalidate_ban_cache(user_id, group_id)
        return user_id, group_id

    async def is_plugin_enabled(self, group_id: str, plugin_module: str) -> bool:
        if is_plugin_protected(plugin_module):
            return True

        cached = await permission_cache.get_group_disabled_plugins(group_id)
        if cached is not None:
            disabled = cached
        else:
            disabled = await permission_state_repository.get_group_disabled_plugins(
                group_id
            )
            await permission_cache.set_group_disabled_plugins(group_id, disabled)

        return plugin_module not in disabled

    async def is_group_bot_enabled(self, group_id: str) -> bool:
        cached = await permission_cache.get_group_bot_enabled(group_id)
        if cached is not None:
            return cached

        enabled = await permission_state_repository.get_group_bot_status(group_id)
        await permission_cache.set_group_bot_enabled(group_id, enabled=enabled)
        return enabled

    async def is_plugin_globally_enabled(self, plugin_module: str) -> bool:
        if is_plugin_protected(plugin_module):
            return True

        cached = await permission_cache.get_plugin_global_enabled(plugin_module)
        if cached is not None:
            return cached

        value = await permission_state_repository.get_plugin_global_enabled(
            plugin_module
        )
        await permission_cache.set_plugin_global_enabled(
            plugin_module,
            enabled=value,
        )
        return value

    async def check_permission(
        self,
        user_id: str,
        group_id: str,
        required_level: int,
    ) -> bool:
        level = await self.get_user_level(user_id, group_id)
        return level >= required_level

    async def assert_can_run_plugin(
        self,
        bot: Bot,
        event: Event,
        plugin: object,
    ) -> None:
        context = await self.build_context(bot, event)
        if context is None:
            return

        if not await self.is_plugin_globally_enabled(plugin.module_name):  # type: ignore[attr-defined]
            logger.debug("Blocked globally disabled plugin {}", plugin.module_name)  # type: ignore[attr-defined]
            raise IgnoredException("plugin_globally_disabled")

        if context.user_id in nonebot.get_driver().config.superusers:
            return

        if context.group_id:
            await self._assert_group_access(
                bot,
                event,
                context,
                plugin.module_name,  # type: ignore[attr-defined]
            )
        elif context.conversation_type == "private" and await self.is_banned(
            context.user_id
        ):
            logger.debug("Blocked banned user {} in private", context.user_id)
            await permission_feedback_gateway.send_ignored_message(
                bot,
                event,
                t("auth.banned"),
            )
            raise IgnoredException("user_banned")

        await self._assert_plugin_level(bot, event, context, plugin)

    async def _assert_group_access(
        self,
        bot: Bot,
        event: Event,
        context: PermissionContext,
        plugin_module: str,
    ) -> None:
        if context.group_id is None:
            return

        if not await self.is_group_bot_enabled(context.group_id):
            raise IgnoredException("bot_disabled")

        if await self.is_banned(context.user_id, context.group_id):
            logger.debug(
                "Blocked banned user {} in group {}",
                context.user_id,
                context.group_id,
            )
            await permission_feedback_gateway.send_ignored_message(
                bot,
                event,
                t("auth.banned"),
            )
            raise IgnoredException("user_banned")

        if not await self.is_plugin_enabled(context.group_id, plugin_module):
            await permission_feedback_gateway.send_ignored_message(
                bot,
                event,
                t("auth.plugin_disabled"),
            )
            raise IgnoredException("plugin_disabled")

    async def _assert_plugin_level(
        self,
        bot: Bot,
        event: Event,
        context: PermissionContext,
        plugin: object,
    ) -> None:
        extra = get_plugin_extra(plugin)  # type: ignore[arg-type]
        required_level = extra.admin_level if extra else 0
        if required_level <= 0 or context.group_id is None:
            return

        db_level = await self.get_user_level(context.user_id, context.group_id)
        if not can_run_with_level(
            context,
            required_level=required_level,
            db_level=db_level,
        ):
            effective = effective_permission_level(context, db_level=db_level)
            logger.debug(
                "Permission denied: {} needs level {} but has {}",
                context.user_id,
                required_level,
                effective,
            )
            await permission_feedback_gateway.send_ignored_message(
                bot,
                event,
                t(
                    "auth.permission_denied",
                    need=level_display_name(
                        required_level,
                        admin_name=t("auth.level_admin"),
                        owner_name=t("auth.level_owner"),
                    ),
                ),
            )
            raise IgnoredException("insufficient_permission")


permission_service = PermissionService()
