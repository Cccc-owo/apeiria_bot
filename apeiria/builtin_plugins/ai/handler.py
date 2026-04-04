from nonebot import logger
from nonebot.adapters import Bot, Event

from apeiria.shared.i18n import t

from .config import get_ai_config, get_builtin_persona
from .model_factory import get_model_client
from .models import ChatTurn
from .prompt import build_reply_prompt
from .scene import build_scene_context
from .window import ai_window_manager


async def handle_ai_message(bot: Bot, event: Event) -> str | None:
    config = get_ai_config()
    if not config.enabled:
        return None

    scene = build_scene_context(bot, event, config)
    if scene is None or not scene.text:
        return None

    state = ai_window_manager.get_state(scene.session_key)
    if not state.enabled:
        return None

    is_explicitly_invoked = scene.chat_mode == "private" or (
        scene.is_mentioned or scene.matched_trigger is not None
    )
    if not is_explicitly_invoked:
        return None

    persona = get_builtin_persona(state.persona_name) or get_builtin_persona("default")
    assert persona is not None

    prompt = build_reply_prompt(
        scene=scene,
        persona=persona,
        fallback_persona_prompt=config.persona_prompt,
        turns=state.turns,
    )
    reply = await _generate_reply(prompt)
    if not reply:
        fallback = config.error_reply_text.strip() or t("ai.command.error_reply_text")
        return fallback or None

    ai_window_manager.append_turn(
        scene.session_key,
        ChatTurn(
            speaker_id=scene.speaker_id,
            speaker_name=scene.speaker_name,
            user_text=scene.text,
            bot_reply=reply,
        ),
        max_items=max(1, config.max_window_items),
    )
    return reply


async def _generate_reply(prompt: str) -> str | None:
    client = get_model_client()
    reply = await client.generate_text(prompt)
    if reply is None:
        logger.debug("AI plugin reply generation returned no content")
        return None
    return reply.strip()
