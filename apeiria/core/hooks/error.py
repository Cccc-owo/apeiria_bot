"""Error hook — post-run exception handling with Sentry + friendly message."""

from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor

from apeiria.core.i18n import t


@run_postprocessor
async def error_hook(
    matcher: Matcher,
    exception: Exception | None,
    bot: Bot,
    event: Event,
) -> None:
    """Catch unhandled exceptions from matcher execution."""
    if exception is None:
        return

    plugin_name = matcher.plugin.name if matcher.plugin else "unknown"
    try:
        user_id = event.get_user_id()
    except Exception:  # noqa: BLE001
        user_id = "unknown"

    logger.opt(exception=exception).error(
        "Unhandled exception in plugin '{}' (user: {})",
        plugin_name,
        user_id,
    )

    # Report to Sentry
    try:
        import sentry_sdk

        sentry_sdk.set_context(
            "nonebot",
            {
                "plugin": plugin_name,
                "user_id": user_id,
                "session_id": event.get_session_id(),
            },
        )
        sentry_sdk.capture_exception(exception)
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        logger.debug("Failed to report to Sentry")

    # Send friendly error message
    try:
        await bot.send(event, t("common.error"))
    except Exception:  # noqa: BLE001
        logger.debug("Failed to send error message to user")
