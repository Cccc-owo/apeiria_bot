"""Statistics hook — record command usage after execution."""

from nonebot.adapters import Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor


@run_postprocessor
async def stats_hook(
    matcher: Matcher,
    exception: Exception | None,
    event: Event,
) -> None:
    """Record command usage to CommandStatistics table."""
    plugin = matcher.plugin
    if not plugin:
        return

    try:
        user_id = event.get_user_id()
    except Exception:  # noqa: BLE001
        return

    session_id = event.get_session_id()
    group_id: str | None = None
    if session_id != user_id and "_" in session_id:
        parts = session_id.split("_")
        if len(parts) >= 2:  # noqa: PLR2004
            group_id = parts[1] if parts[0] == "group" else parts[0]

    # Determine command name from matcher state
    command = ""
    if hasattr(matcher, "state") and matcher.state:
        cmd = matcher.state.get("_prefix", {}).get("command", ())
        if cmd:
            command = " ".join(cmd) if isinstance(cmd, tuple) else str(cmd)
    if not command:
        command = plugin.name

    try:
        from nonebot_plugin_orm import get_session

        from apeiria.core.models.statistics import CommandStatistics

        async with get_session() as session:
            session.add(
                CommandStatistics(
                    plugin_name=plugin.module_name,
                    command=command,
                    user_id=user_id,
                    group_id=group_id,
                    success=exception is None,
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.debug("Failed to record command statistics")
