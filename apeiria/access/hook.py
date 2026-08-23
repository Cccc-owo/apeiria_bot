"""NoneBot preprocessor hook that enforces access control for plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nonebot import require
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher  # noqa: TC002
from nonebot.message import run_preprocessor
from nonebot.permission import SUPERUSER

require("nonebot_plugin_uninfo")
from nonebot_plugin_uninfo import Uninfo  # noqa: TC002

if TYPE_CHECKING:
    from nonebot_plugin_uninfo import Session

_installed = False


def resolve_subject(session: Session) -> tuple[str, str | None]:
    """Resolve a session into a user id and an optional group id.

    Args:
        session: The uninfo session describing the current event.

    Returns:
        A tuple of the user id and the group id, or None when the event does
        not originate from a group.
    """
    user_id = session.user.id
    group_id = session.scene.id if session.scene.is_group else None
    return user_id, group_id


def check_access(
    plugin_name: str,
    user_id: str,
    group_id: str | None,
    *,
    is_superuser: bool = False,
) -> bool:
    """Return whether the user is allowed to access the given plugin.

    Args:
        plugin_name: The name of the plugin being accessed.
        user_id: The identifier of the user requesting access.
        group_id: The identifier of the group the event originates from,
            or None when not in a group.
        is_superuser: Whether the user is a superuser; superusers are always
            granted access.

    Returns:
        True if access is allowed, False otherwise.
    """
    from apeiria.bootstrap.steps import get_access_control

    return get_access_control().evaluate(
        user_id, group_id, plugin_name, is_superuser=is_superuser
    )


async def access_preprocessor(
    matcher: Matcher,
    bot: Bot,
    event: Event,
    session: Uninfo,
) -> None:
    """Enforce access control before a matcher processes an event.

    Args:
        matcher: The matcher about to process the event.
        bot: The bot receiving the event.
        event: The incoming event.
        session: The uninfo session describing the current event.

    Raises:
        IgnoredException: If access control denies the matched plugin.
    """
    user_id, group_id = resolve_subject(session)
    plugin_name = matcher.plugin_name or ""
    if await SUPERUSER(bot, event):
        return
    if not check_access(plugin_name, user_id, group_id):
        raise IgnoredException("blocked by access control")  # noqa: TRY003


def install_access_hook() -> None:
    """Install the access control preprocessor hook.

    Registers the access preprocessor with NoneBot's run_preprocessor hook.
    This is a no-op if the hook has already been installed.
    """
    global _installed  # noqa: PLW0603
    if _installed:
        return
    run_preprocessor(access_preprocessor)
    _installed = True
