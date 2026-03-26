"""Statistics hook — record command usage after execution."""

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor

from apeiria.domains.statistics import statistics_service


@run_postprocessor
async def stats_hook(
    matcher: Matcher,
    exception: Exception | None,
    event: Event,
) -> None:
    """Record command usage to CommandStatistics table."""
    await statistics_service.record_matcher_execution(
        matcher,
        event,
        success=exception is None,
    )
