"""Implement the ``/access`` command for managing access control rules."""

from __future__ import annotations

from arclet.alconna import Args, CommandMeta
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot_plugin_alconna import Alconna, Match, on_alconna
from sqlalchemy import select

from apeiria.db.engine import get_db
from apeiria.db.models.access import AccessRule

from .utils import ensure_owner_message

_USAGE_ADD = "用法见帮助: /access add allow|deny user|group ID 插件名"
_USAGE_RM = "用法见帮助: /access remove user|group ID 插件名"

_access = on_alconna(
    Alconna(
        "access",
        Args["action", str],
        Args["arg1?", str],
        Args["arg2?", str],
        Args["arg3?", str],
        Args["arg4?", str],
        Args["arg5?", str],
        meta=CommandMeta(description="管理权限规则"),
    ),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_access.handle()
async def handle_access(  # noqa: PLR0913, PLR0917
    bot: Bot,
    event: Event,
    action: Match[str],
    arg1: Match[str],
    arg2: Match[str],
    arg3: Match[str],
    arg4: Match[str],
    arg5: Match[str],
) -> None:
    """Handle the ``/access`` command and dispatch based on the requested action.

    Args:
        bot: The bot instance used to send responses.
        event: The message event that triggered the command.
        action: The command action, one of list/add/remove.
        arg1: The first positional argument.
        arg2: The second positional argument.
        arg3: The third positional argument.
        arg4: The fourth positional argument.
        arg5: The fifth positional argument.
    """
    owner_error = await ensure_owner_message(bot, event)
    if owner_error:
        await _access.finish(owner_error)

    selected = action.result.strip().lower()

    if selected == "list":
        await _access.finish(await _list_rules())

    if selected == "add":
        if not all((arg1.available, arg2.available, arg3.available, arg4.available)):
            await _access.finish(_USAGE_ADD)
            return
        await _access.finish(
            await _add_rule(
                arg1.result,
                arg2.result,
                arg3.result,
                arg4.result,
                arg5.result if arg5.available else "0",
            )
        )

    if selected == "remove":
        if not all((arg1.available, arg2.available, arg3.available)):
            await _access.finish(_USAGE_RM)
            return
        await _access.finish(await _del_rule(arg1.result, arg2.result, arg3.result))

    await _access.finish("操作无效，可选: list / add / remove")


async def _list_rules() -> str:
    """Query and format all current access control rules.

    Returns:
        A formatted text describing the rules, or an empty-state message when
        no rules are configured.
    """
    db = get_db()
    async with db.gate.read() as sess:
        rules = list((await sess.execute(select(AccessRule))).scalars().all())
    if not rules:
        return "暂无权限规则"
    lines = [
        f"- [{r.action}] {r.subject_type}:{r.subject_id}"
        f" → {r.plugin_name or '全局'} p={r.priority}"
        for r in rules
    ]
    return "权限规则:\n\n" + "\n".join(lines)


async def _reload_access() -> None:
    """Reload the access control snapshot so DB changes take effect immediately."""
    from apeiria.bootstrap.steps import get_access_control

    await get_access_control().load_snapshot()


async def _add_rule(
    effect: str,
    subject_type: str,
    subject_id: str,
    plugin_query: str,
    priority: str = "0",
) -> str:
    """Add an access control rule and reload the access snapshot.

    Args:
        effect: The access effect, either allow or deny.
        subject_type: The rule subject type, either user or group.
        subject_id: The rule subject ID.
        plugin_query: The plugin query; global targets all plugins.
        priority: The rule priority, defaulting to 0.

    Returns:
        A message describing the result of the addition.
    """
    normalized_effect = effect.strip().lower()
    normalized_type = subject_type.strip().lower()
    if normalized_effect not in {"allow", "deny"}:
        return _USAGE_ADD
    if normalized_type not in {"user", "group"}:
        return _USAGE_ADD

    try:
        priority_int = int(priority)
    except (ValueError, TypeError):
        priority_int = 0

    q = plugin_query.strip().lower()
    plugin_name = None if q == "global" else plugin_query.strip()
    db = get_db()
    async with db.gate.write() as sess:
        rule = AccessRule(
            subject_type=normalized_type,
            subject_id=subject_id.strip(),
            plugin_name=plugin_name,
            action=normalized_effect,
            priority=priority_int,
        )
        sess.add(rule)
        await sess.flush()
    await _reload_access()
    target = plugin_name or "全局"
    return f"已添加: {normalized_effect} {normalized_type}:{subject_id} → {target}"


async def _del_rule(
    subject_type: str,
    subject_id: str,
    plugin_query: str,
) -> str:
    """Delete matching access control rules and reload the access snapshot.

    Args:
        subject_type: The rule subject type, either user or group.
        subject_id: The rule subject ID.
        plugin_query: The plugin query; global targets all plugins.

    Returns:
        A message describing the deletion result, or a not-found message when
        no rule matches.
    """
    normalized_type = subject_type.strip().lower()
    if normalized_type not in {"user", "group"}:
        return _USAGE_RM

    q = plugin_query.strip().lower()
    plugin_name = None if q == "global" else plugin_query.strip()
    db = get_db()
    async with db.gate.write() as sess:
        stmt = select(AccessRule).where(
            AccessRule.subject_type == normalized_type,
            AccessRule.subject_id == subject_id.strip(),
            AccessRule.plugin_name == plugin_name,
        )
        rules = list((await sess.execute(stmt)).scalars().all())
        if not rules:
            return "未找到匹配的权限规则"
        for rule in rules:
            await sess.delete(rule)
        await sess.flush()
    await _reload_access()
    return f"已移除 {len(rules)} 条权限规则"
