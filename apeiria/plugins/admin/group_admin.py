"""Owner-facing group management commands."""

from __future__ import annotations

from arclet.alconna import Args, CommandMeta
from nonebot.adapters import Event  # noqa: TC002
from nonebot_plugin_alconna import Alconna, Match, on_alconna

from apeiria.core.i18n import t
from apeiria.domains.access import access_service
from apeiria.domains.access.runtime import group_id_from_event
from apeiria.domains.groups import group_service
from apeiria.domains.plugins import plugin_policy_service

from .presenter import render_block
from .utils import ensure_owner_message, resolve_plugin_catalog_query

_group = on_alconna(
    Alconna(
        "group",
        Args["action", str],
        Args["arg1?", str],
        Args["arg2?", str],
        meta=CommandMeta(description="管理当前群的 bot、插件与访问状态"),
    ),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_group.handle()
async def handle_group(
    event: Event,
    action: Match[str],
    arg1: Match[str],
    arg2: Match[str],
) -> None:
    owner_error = ensure_owner_message(event)
    if owner_error:
        await _group.finish(owner_error)

    group_id = group_id_from_event(event)
    if group_id is None:
        await _group.finish(t("admin.group.group_only"))

    selected_action = action.result.strip().lower()
    if selected_action == "status":
        await _group.finish(await _render_group_status(group_id))
    if selected_action == "bot":
        if not arg1.available:
            await _group.finish(t("admin.group.bot_usage"))
        await _group.finish(await _toggle_group_bot(group_id, arg1.result))
    if selected_action == "plugin":
        if not (arg1.available and arg2.available):
            await _group.finish(t("admin.group.plugin_usage"))
        await _group.finish(
            await _toggle_group_plugin(
                group_id,
                state=arg1.result,
                plugin_query=arg2.result,
            )
        )
    if selected_action == "access":
        if not arg1.available:
            await _group.finish(t("admin.group.access_usage"))
        await _group.finish(await _render_group_plugin_access(group_id, arg1.result))

    await _group.finish(t("admin.group.invalid_action"))


async def _render_group_status(group_id: str) -> str:
    group = await group_service.get_group(group_id)
    disabled_plugins = ", ".join(group.disabled_plugins) or t("admin.common.none")
    return render_block(
        t("admin.group.status_title"),
        [
            (t("admin.group.field_group_id"), group.group_id),
            (
                t("admin.group.field_group_name"),
                group.group_name or t("admin.common.none"),
            ),
            (
                t("admin.group.field_bot_status"),
                t("admin.common.enabled")
                if group.bot_status
                else t("admin.common.disabled"),
            ),
            (t("admin.group.field_disabled_plugins"), disabled_plugins),
        ],
    )


async def _toggle_group_bot(group_id: str, raw_state: str) -> str:
    state = raw_state.strip().lower()
    if state not in {"on", "off"}:
        return t("admin.group.bot_usage")
    enabled = state == "on"
    await group_service.update_group_status(group_id, enabled=enabled)
    return t(
        "admin.group.bot_updated",
        group_id=group_id,
        status=t("admin.common.enabled") if enabled else t("admin.common.disabled"),
    )


async def _toggle_group_plugin(
    group_id: str,
    *,
    state: str,
    plugin_query: str,
) -> str:
    normalized_state = state.strip().lower()
    raw_plugin_query = plugin_query.strip()
    if normalized_state not in {"on", "off"} or not raw_plugin_query:
        return t("admin.group.plugin_usage")

    item, candidates = await resolve_plugin_catalog_query(
        raw_plugin_query,
        allow_fuzzy=True,
    )
    if candidates:
        return t(
            "admin.plugin.ambiguous",
            name=raw_plugin_query,
            candidates=", ".join(candidates),
        )
    if item is None:
        return t("admin.plugin.not_found", name=raw_plugin_query)

    await group_service.toggle_group_plugin(
        group_id,
        item.module_name,
        enable=normalized_state == "on",
    )
    return t(
        "admin.group.plugin_updated",
        group_id=group_id,
        plugin=item.name,
        status=(
            t("admin.common.enabled")
            if normalized_state == "on"
            else t("admin.common.disabled")
        ),
    )


async def _render_group_plugin_access(group_id: str, plugin_query: str) -> str:
    item, candidates = await resolve_plugin_catalog_query(
        plugin_query,
        allow_fuzzy=True,
    )
    if candidates:
        return t(
            "admin.plugin.ambiguous",
            name=plugin_query,
            candidates=", ".join(candidates),
        )
    if item is None:
        return t("admin.plugin.not_found", name=plugin_query)

    group = await group_service.get_group(group_id)
    spec = await plugin_policy_service.get_access_spec(item.module_name)
    group_rule = next(
        (
            rule
            for rule in await access_service.list_access_rules()
            if rule.plugin_module == item.module_name
            if rule.subject_type == "group" and rule.subject_id == group_id
        ),
        None,
    )
    return render_block(
        t("admin.group.access_title", name=item.name),
        [
            (t("admin.group.field_group_id"), group_id),
            (t("admin.plugin.field_module"), item.module_name),
            (
                t("admin.group.field_bot_status"),
                t("admin.common.enabled")
                if group.bot_status
                else t("admin.common.disabled"),
            ),
            (
                t("admin.group.field_plugin_status"),
                t("admin.common.disabled")
                if item.module_name in group.disabled_plugins
                else t("admin.common.enabled"),
            ),
            (t("admin.access.field_access_mode"), spec.access_mode),
            (t("admin.access.field_required_level"), spec.required_level),
            (
                t("admin.group.field_group_rule"),
                group_rule.effect if group_rule else t("admin.common.none"),
            ),
        ],
    )
