# pyright: reportAttributeAccessIssue=false
"""Shared helpers for the admin builtin plugin.

This module provides utilities to resolve plugin queries to a loaded plugin and
to verify that an event was sent by a superuser.
"""

from __future__ import annotations

import nonebot
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.permission import SUPERUSER


def resolve_plugin_query(
    query: str,
    *,
    allow_fuzzy: bool,
) -> tuple[nonebot.plugin.Plugin | None, list[str]]:
    """Resolve a plugin query to a loaded plugin or a list of candidates.

    Args:
        query: The plugin query string to resolve.
        allow_fuzzy: Whether to allow a single fuzzy match to be resolved.

    Returns:
        A tuple whose first element is the uniquely resolved plugin, or ``None``
        when there is no unique match, and whose second element is the sorted
        list of candidate display strings when the match is ambiguous.
    """
    normalized = query.strip().lower()
    if not normalized:
        return None, []

    exact_matches: list[nonebot.plugin.Plugin] = []
    fuzzy_matches: list[nonebot.plugin.Plugin] = []
    for plugin in nonebot.get_loaded_plugins():
        candidates = [
            plugin.module_name.lower(),
            plugin.id_.lower(),
        ]
        if normalized in candidates:
            exact_matches.append(plugin)
            continue
        if any(normalized in candidate for candidate in candidates):
            fuzzy_matches.append(plugin)

    resolved: nonebot.plugin.Plugin | None = None
    candidates: list[str] = []
    if len(exact_matches) == 1:
        resolved = exact_matches[0]
    elif exact_matches:
        candidates = sorted({f"{p.id_} ({p.module_name})" for p in exact_matches})
    elif len(fuzzy_matches) == 1 and allow_fuzzy:
        resolved = fuzzy_matches[0]
    elif fuzzy_matches:
        candidates = sorted({f"{p.id_} ({p.module_name})" for p in fuzzy_matches})
    return resolved, candidates


async def is_owner_event(bot: Bot, event: Event) -> bool:
    """Return whether the event was sent by a superuser.

    Args:
        bot: The bot instance handling the event.
        event: The triggering event.
    """
    return await SUPERUSER(bot, event)


async def ensure_owner_message(bot: Bot, event: Event) -> str | None:
    """Return an error message when the event was not sent by a superuser.

    Args:
        bot: The bot instance handling the event.
        event: The triggering event.

    Returns:
        ``None`` when the event sender is a superuser, otherwise an error
        message string.
    """
    if await is_owner_event(bot, event):
        return None
    return "仅限超级用户使用"
