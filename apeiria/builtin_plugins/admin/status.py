"""Provide the ``/status`` command that reports the bot's runtime status.

This module registers an Alconna matcher that replies with a formatted block
showing uptime, running state, loaded plugin count, and enabled adapters.
"""

from __future__ import annotations

import time

import nonebot
from arclet.alconna import CommandMeta
from nonebot.adapters import Bot, Event  # noqa: TC002
from nonebot_plugin_alconna import Alconna, on_alconna

from .presenter import render_block
from .utils import ensure_owner_message

_start_time = time.monotonic()

_status = on_alconna(
    Alconna("status", meta=CommandMeta(description="查看运行状态")),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_status.handle()
async def handle_status(bot: Bot, event: Event) -> None:
    """Reply to the status command with a formatted runtime status block.

    Args:
        bot: The bot instance that invoked the command.
        event: The triggering event.
    """
    owner_error = await ensure_owner_message(bot, event)
    if owner_error:
        await _status.finish(owner_error)

    uptime = int(time.monotonic() - _start_time)
    plugins_count = len(nonebot.get_loaded_plugins())
    adapters = (
        ", ".join(type(a).__name__ for a in nonebot.get_adapters().values()) or "无"
    )

    await _status.finish(
        render_block(
            "运行状态",
            [
                ("运行时间", f"{uptime}s"),
                ("状态", "运行中"),
                ("已加载插件", plugins_count),
                ("适配器", adapters),
            ],
        )
    )
