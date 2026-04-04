from nonebot import on_message
from nonebot.adapters import Bot, Event

from .handler import handle_ai_message

_ai_message = on_message(priority=50, block=False)


@_ai_message.handle()
async def handle_ai_event(bot: Bot, event: Event) -> None:
    reply = await handle_ai_message(bot, event)
    if not reply:
        return
    await bot.send(event, reply)
