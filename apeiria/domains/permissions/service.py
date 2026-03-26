"""Permission domain services."""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

import nonebot
from nonebot.exception import IgnoredException
from nonebot.log import logger

from apeiria.core.i18n import t
from apeiria.core.services.cache import get_cache
from apeiria.core.utils.helpers import get_plugin_extra, is_plugin_protected

if TYPE_CHECKING:
    from nonebot.adapters import Bot, Event


ConversationType = Literal["private", "group", "other"]


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
        if session_id == user_id:
            return None
        if "_" in session_id:
            parts = session_id.split("_")
            if len(parts) >= 2:  # noqa: PLR2004
                return parts[1] if parts[0] == "group" else parts[0]
        return None

    async def build_context(self, bot: Bot, event: Event) -> PermissionContext | None:
        """Build a normalized permission context from an abstract event."""
        try:
            user_id = event.get_user_id()
        except Exception:  # noqa: BLE001
            return None

        group_id = self._group_id_from_event(event)
        conversation_type: ConversationType = "other"
        if group_id is not None:
            conversation_type = "group"
        elif self._is_private_event(event, user_id):
            conversation_type = "private"

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

    async def invalidate_user_level_cache(self, user_id: str, group_id: str) -> None:
        await get_cache().delete(f"perm:{user_id}:{group_id}")

    async def invalidate_ban_cache(
        self,
        user_id: str,
        group_id: str | None = None,
    ) -> None:
        cache = get_cache()
        await cache.delete(f"ban:{user_id}")
        if group_id:
            await cache.delete(f"ban:{user_id}:{group_id}")

    async def invalidate_group_plugin_cache(self, group_id: str) -> None:
        await get_cache().delete(f"group_plugin:{group_id}")

    async def invalidate_group_bot_status_cache(self, group_id: str) -> None:
        await get_cache().delete(f"group_bot:{group_id}")

    async def invalidate_plugin_global_cache(self, plugin_module: str) -> None:
        await get_cache().delete(f"plugin_global:{plugin_module}")

    async def get_user_level(self, user_id: str, group_id: str) -> int:
        cache = get_cache()
        cache_key = f"perm:{user_id}:{group_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return int(cached)

        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.level import LevelUser

        async with get_session() as session:
            result = await session.execute(
                select(LevelUser.level).where(
                    LevelUser.user_id == user_id,
                    LevelUser.group_id == group_id,
                )
            )
            row = result.scalar_one_or_none()
            level = row if row is not None else 0

        await cache.set(cache_key, level, ttl=300)
        return level

    async def list_user_levels(self) -> list[tuple[str, str, int]]:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.level import LevelUser

        async with get_session() as session:
            result = await session.execute(select(LevelUser))
            rows = result.scalars().all()
        return [(row.user_id, row.group_id, row.level) for row in rows]

    async def set_user_level(self, user_id: str, group_id: str, level: int) -> None:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.level import LevelUser

        async with get_session() as session:
            result = await session.execute(
                select(LevelUser).where(
                    LevelUser.user_id == user_id,
                    LevelUser.group_id == group_id,
                )
            )
            record = result.scalar_one_or_none()
            if record:
                record.level = level
            else:
                session.add(LevelUser(user_id=user_id, group_id=group_id, level=level))
            await session.commit()

        await self.invalidate_user_level_cache(user_id, group_id)
        logger.debug("Set level {}:{} -> {}", user_id, group_id, level)

    async def is_banned(self, user_id: str, group_id: str | None = None) -> bool:
        cache = get_cache()
        cache_key = f"ban:{user_id}"
        if group_id:
            cache_key += f":{group_id}"

        cached = await cache.get(cache_key)
        if cached is not None:
            return bool(cached)

        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.ban import BanConsole

        async with get_session() as session:
            stmt = select(BanConsole).where(BanConsole.user_id == user_id)
            if group_id:
                stmt = stmt.where(
                    (BanConsole.group_id == group_id) | (BanConsole.group_id.is_(None))
                )
            result = await session.execute(stmt)
            bans = result.scalars().all()

        now = datetime.now(timezone.utc)
        banned = False
        for ban in bans:
            if ban.duration == 0:
                banned = True
                break
            if ban.ban_time and ban.duration > 0:
                ban_time = ban.ban_time
                if ban_time.tzinfo is None:
                    ban_time = ban_time.replace(tzinfo=timezone.utc)
                if (now - ban_time).total_seconds() < ban.duration:
                    banned = True
                    break

        await cache.set(cache_key, banned, ttl=60)
        return banned

    async def list_bans(
        self,
    ) -> list[tuple[int, str | None, str | None, int, str | None]]:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.ban import BanConsole

        async with get_session() as session:
            result = await session.execute(select(BanConsole))
            rows = result.scalars().all()
        return [
            (row.id, row.user_id, row.group_id, row.duration, row.reason)
            for row in rows
        ]

    async def create_ban(
        self,
        *,
        user_id: str,
        group_id: str | None,
        duration: int,
        reason: str | None,
    ) -> tuple[int, str | None, str | None, int, str | None]:
        from nonebot_plugin_orm import get_session

        from apeiria.core.models.ban import BanConsole

        async with get_session() as session:
            record = BanConsole(
                user_id=user_id,
                group_id=group_id,
                ban_time=datetime.now(timezone.utc),
                duration=duration,
                reason=reason,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)

        await self.invalidate_ban_cache(user_id, group_id)
        return (
            record.id,
            record.user_id,
            record.group_id,
            record.duration,
            record.reason,
        )

    async def delete_ban(self, ban_id: int) -> tuple[str | None, str | None]:
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.ban import BanConsole
        from apeiria.domains.exceptions import ResourceNotFoundError

        async with get_session() as session:
            result = await session.execute(
                select(BanConsole).where(BanConsole.id == ban_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise ResourceNotFoundError(t("web_ui.permissions.ban_not_found"))

            user_id = record.user_id
            group_id = record.group_id
            await session.delete(record)
            await session.commit()

        if user_id:
            await self.invalidate_ban_cache(user_id, group_id)
        return user_id, group_id

    async def is_plugin_enabled(self, group_id: str, plugin_module: str) -> bool:
        if is_plugin_protected(plugin_module):
            return True

        cache = get_cache()
        cache_key = f"group_plugin:{group_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            disabled = list(cached)
        else:
            from nonebot_plugin_orm import get_session
            from sqlalchemy import select

            from apeiria.core.models.group import GroupConsole

            async with get_session() as session:
                result = await session.execute(
                    select(GroupConsole.disabled_plugins).where(
                        GroupConsole.group_id == group_id
                    )
                )
                raw = result.scalar_one_or_none()
                try:
                    disabled = json.loads(raw) if raw else []
                except (json.JSONDecodeError, TypeError):
                    disabled = []
            await cache.set(cache_key, disabled, ttl=120)

        return plugin_module not in disabled

    async def is_group_bot_enabled(self, group_id: str) -> bool:
        cache = get_cache()
        cache_key = f"group_bot:{group_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return bool(cached)

        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.group import GroupConsole

        async with get_session() as session:
            result = await session.execute(
                select(GroupConsole.bot_status).where(GroupConsole.group_id == group_id)
            )
            bot_status = result.scalar_one_or_none()

        enabled = bot_status is not False
        await cache.set(cache_key, enabled, ttl=120)
        return enabled

    async def is_plugin_globally_enabled(self, plugin_module: str) -> bool:
        if is_plugin_protected(plugin_module):
            return True

        cache = get_cache()
        cache_key = f"plugin_global:{plugin_module}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return bool(cached)

        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from apeiria.core.models.plugin_info import PluginInfo

        async with get_session() as session:
            result = await session.execute(
                select(PluginInfo.is_global_enabled).where(
                    PluginInfo.module_name == plugin_module
                )
            )
            enabled = result.scalar_one_or_none()

        value = True if enabled is None else bool(enabled)
        await cache.set(cache_key, value, ttl=120)
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
            await self._send_ignored_message(bot, event, t("auth.banned"))
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
            await self._send_ignored_message(bot, event, t("auth.banned"))
            raise IgnoredException("user_banned")

        if not await self.is_plugin_enabled(context.group_id, plugin_module):
            await self._send_ignored_message(bot, event, t("auth.plugin_disabled"))
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

        if context.adapter_role_level >= required_level:
            return

        db_level = await self.get_user_level(context.user_id, context.group_id)
        effective = max(context.adapter_role_level, db_level)
        if effective < required_level:
            logger.debug(
                "Permission denied: {} needs level {} but has {}",
                context.user_id,
                required_level,
                effective,
            )
            level_names = {5: t("auth.level_admin"), 6: t("auth.level_owner")}
            await self._send_ignored_message(
                bot,
                event,
                t(
                    "auth.permission_denied",
                    need=level_names.get(required_level, f"Lv.{required_level}"),
                ),
            )
            raise IgnoredException("insufficient_permission")

    def _group_id_from_event(self, event: Event) -> str | None:
        group_id = getattr(event, "group_id", None)
        if group_id is not None:
            return str(group_id)

        try:
            user_id = event.get_user_id()
            return self.extract_group_id(event.get_session_id(), user_id)
        except Exception:  # noqa: BLE001
            return None

    def _is_private_event(self, event: Event, user_id: str) -> bool:
        detail_type = getattr(event, "detail_type", None)
        if detail_type == "private":
            return True
        try:
            return event.get_session_id() == user_id
        except Exception:  # noqa: BLE001
            return False

    async def _send_ignored_message(self, bot: Bot, event: Event, message: str) -> None:
        with contextlib.suppress(Exception):
            await bot.send(event, message)


permission_service = PermissionService()
