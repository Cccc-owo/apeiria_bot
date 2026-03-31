"""Runtime feedback helpers for denied plugin execution."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nonebot.adapters import Bot, Event

    from apeiria.app.access.models import Decision


class GuardFeedbackService:
    """Best-effort runtime feedback for denied access decisions."""

    async def handle_denied(self, bot: Bot, event: Event, decision: Decision) -> None:
        if not decision.message:
            return
        with contextlib.suppress(Exception):
            await bot.send(event, decision.message)


guard_feedback_service = GuardFeedbackService()
