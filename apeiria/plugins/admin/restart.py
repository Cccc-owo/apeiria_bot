"""Owner-facing restart command."""

from __future__ import annotations

from arclet.alconna import CommandMeta
from nonebot.adapters import Event  # noqa: TC002
from nonebot_plugin_alconna import Alconna, on_alconna

from apeiria.core.i18n import t
from apeiria.domains.dashboard import dashboard_service

from .utils import ensure_owner_message

_restart = on_alconna(
    Alconna("restart", meta=CommandMeta(description="安排 bot 进程重启")),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_restart.handle()
async def handle_restart(event: Event) -> None:
    owner_error = ensure_owner_message(event)
    if owner_error:
        await _restart.finish(owner_error)

    dashboard_service.schedule_restart()
    await _restart.finish(t("admin.restart.scheduled"))
