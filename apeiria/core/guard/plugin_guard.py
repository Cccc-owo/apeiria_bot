"""Unified runtime guard for plugin execution."""

from __future__ import annotations

from nonebot.exception import IgnoredException
from nonebot.log import logger

from apeiria.core.i18n import t
from apeiria.domains.access import (
    AccessContext,
    Decision,
    PluginAccessSpec,
    access_service,
)
from apeiria.domains.plugins import plugin_policy_service


class PluginGuardService:
    """Evaluate plugin runtime access for all incoming matcher executions."""

    async def evaluate(self, bot, event, plugin) -> Decision:  # noqa: ANN001
        context = await access_service.build_context(bot, event)
        if context is None:
            return self._allow()

        plugin_module = plugin.module_name  # type: ignore[attr-defined]
        spec = await plugin_policy_service.get_access_spec(plugin_module)
        decision = await self._evaluate_plugin_state(
            context.group_id,
            spec,
        )
        if decision is not None:
            return decision

        if context.is_superuser:
            return self._allow()

        decision = await self._evaluate_access_rules(
            context,
            plugin_module,
            spec.access_mode,
        )
        if decision is not None:
            return decision

        effective_level = await access_service.get_effective_level(context)
        if effective_level >= spec.required_level:
            return self._allow()

        logger.debug(
            "Access denied by level: user={} plugin={} need={} have={}",
            context.user_id,
            plugin_module,
            spec.required_level,
            effective_level,
        )
        return Decision(
            allowed=False,
            code="insufficient_level",
            message=t("auth.permission_denied", need=f"Lv.{spec.required_level}"),
        )

    async def assert_allowed(self, bot, event, plugin) -> None:  # noqa: ANN001
        from apeiria.core.guard.feedback import guard_feedback_service

        decision = await self.evaluate(bot, event, plugin)
        if decision.allowed:
            return
        await guard_feedback_service.handle_denied(bot, event, decision)
        raise IgnoredException(decision.code)

    async def _evaluate_plugin_state(
        self,
        group_id: str | None,
        spec: PluginAccessSpec,
    ) -> Decision | None:
        is_enabled = await plugin_policy_service.is_globally_enabled(spec.plugin_module)
        if spec.protection_mode != "required" and not is_enabled:
            return Decision(allowed=False, code="plugin_globally_disabled")

        if group_id is None:
            return None
        if not await access_service.is_group_bot_enabled(group_id):
            return Decision(allowed=False, code="bot_disabled_in_group")
        if await access_service.is_group_plugin_enabled(group_id, spec.plugin_module):
            return None
        return Decision(
            allowed=False,
            code="plugin_disabled_in_group",
            message=t("auth.plugin_disabled"),
        )

    async def _evaluate_access_rules(
        self,
        context: AccessContext,
        plugin_module: str,
        access_mode: str,
    ) -> Decision | None:
        explicit_rule = await access_service.get_explicit_rule(context, plugin_module)
        if explicit_rule is None:
            if access_mode == "default_deny":
                return Decision(
                    allowed=False,
                    code="access_not_allowed_by_default",
                    message=t("auth.access_not_allowed"),
                )
            return None
        if explicit_rule.effect != "deny":
            return None
        return Decision(
            allowed=False,
            code=(
                "access_denied_by_user_rule"
                if explicit_rule.subject_type == "user"
                else "access_denied_by_group_rule"
            ),
        )

    def _allow(self) -> Decision:
        return Decision(allowed=True, code="ok")


plugin_guard_service = PluginGuardService()
