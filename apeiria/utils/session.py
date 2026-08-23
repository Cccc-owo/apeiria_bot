"""Helpers for deriving scoped identifiers from sessions and superuser targets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nonebot import get_driver
from nonebot.adapters import Bot  # noqa: TC002
from nonebot.log import logger

if TYPE_CHECKING:
    from nonebot_plugin_uninfo import Session


def scoped_group_id(session: Session) -> str:
    """Return the scope-prefixed group ID for a session.

    Args:
        session: The session to derive the group ID from.

    Returns:
        The group ID formatted as ``{scope}:{scene.id}``.
    """
    return f"{session.scope}:{session.scene.id}"


def scoped_user_id(session: Session) -> str:
    """Return the scope-prefixed user ID for a session.

    Args:
        session: The session to derive the user ID from.

    Returns:
        The user ID formatted as ``{scope}:{user.id}``.
    """
    return f"{session.scope}:{session.user.id}"


def resolve_superuser_targets(bot: Bot) -> list[str]:
    """Resolve the superusers usable by a bot into target IDs for its adapter.

    Each configured superuser is matched against the bot's adapter prefix: a
    ``adapter:user`` entry yields ``user``, a bare entry is kept as-is, and an
    entry for a different adapter is skipped. Logs a warning when no target
    remains.

    Args:
        bot: The bot whose adapter prefix is used for matching.

    Returns:
        The list of superuser target IDs for this adapter.
    """
    adapter_prefix = bot.adapter.get_name().split(maxsplit=1)[0].lower()
    superusers = get_driver().config.superusers
    targets: list[str] = []
    for s in superusers:
        if not s:
            continue
        if s.startswith(f"{adapter_prefix}:"):
            targets.append(s.split(":", 1)[1])
        elif ":" not in s:
            targets.append(s)
    if not targets:
        logger.warning(
            "当前 bot ({}) 无同平台超管配置 (adapter={})",
            bot.self_id,
            bot.adapter.get_name(),
        )
    return targets
