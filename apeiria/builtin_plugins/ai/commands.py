from arclet.alconna import Args, CommandMeta
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import Alconna, Match, on_alconna

from apeiria.shared.i18n import t

from .config import get_builtin_persona, get_builtin_personas
from .window import ai_window_manager

_ai = on_alconna(
    Alconna(
        "ai",
        Args["action?", str],
        meta=CommandMeta(description=t("ai.command.ai_description")),
    ),
    use_cmd_start=True,
    priority=5,
    block=True,
)

_persona = on_alconna(
    Alconna(
        "persona",
        Args["action?", str],
        Args["name?", str],
        meta=CommandMeta(description=t("ai.command.persona_description")),
    ),
    use_cmd_start=True,
    priority=5,
    block=True,
)

_reset = on_alconna(
    Alconna("reset", meta=CommandMeta(description=t("ai.command.reset_description"))),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@_ai.handle()
async def handle_ai(bot: Bot, event: Event, action: Match[str]) -> None:
    session_key = _build_session_key(bot, event)
    state = ai_window_manager.get_state(session_key)
    selected = action.result.strip().lower() if action.available else ""
    status = (
        t("ai.command.ai_status_enabled")
        if state.enabled
        else t("ai.command.ai_status_disabled")
    )

    if not selected:
        await _ai.finish(
            t(
                "ai.command.ai_status_with_usage",
                status=status,
                persona=state.persona_name,
            )
        )

    if selected == "on":
        ai_window_manager.set_enabled(session_key, enabled=True)
        await _ai.finish(t("ai.command.ai_enabled"))
    if selected == "off":
        ai_window_manager.set_enabled(session_key, enabled=False)
        await _ai.finish(t("ai.command.ai_disabled"))
    if selected == "status":
        await _ai.finish(
            t("ai.command.ai_status", status=status, persona=state.persona_name)
        )

    await _ai.finish(t("ai.command.ai_usage"))


@_persona.handle()
async def handle_persona(
    bot: Bot,
    event: Event,
    action: Match[str],
    name: Match[str],
) -> None:
    session_key = _build_session_key(bot, event)
    state = ai_window_manager.get_state(session_key)
    selected = action.result.strip().lower() if action.available else ""

    if not selected:
        await _persona.finish(
            t(
                "ai.command.persona_current_with_usage",
                persona=state.persona_name,
            )
        )

    if selected == "list":
        personas = "\n".join(
            f"- {persona.name}: {persona.label}" for persona in get_builtin_personas()
        )
        await _persona.finish(f"{t('ai.command.persona_list_title')}\n{personas}")

    if selected == "show":
        await _persona.finish(
            t("ai.command.persona_current", persona=state.persona_name)
        )

    if selected == "use":
        if not name.available:
            await _persona.finish(t("ai.command.persona_use_usage"))
        persona = get_builtin_persona(name.result)
        if persona is None:
            await _persona.finish(t("ai.command.persona_not_found", name=name.result))
        ai_window_manager.set_persona(session_key, persona.name)
        await _persona.finish(t("ai.command.persona_switched", label=persona.label))

    await _persona.finish(t("ai.command.persona_usage"))


@_reset.handle()
async def handle_reset(bot: Bot, event: Event) -> None:
    session_key = _build_session_key(bot, event)
    ai_window_manager.clear_turns(session_key)
    await _reset.finish(t("ai.command.reset_done"))



def _build_session_key(bot: Bot, event: Event) -> str:
    session_id = _safe_get_session_id(event) or _safe_get_user_id(event) or "unknown"
    message_type = _resolve_message_type(event)
    return f"{bot.self_id}:{message_type}:{session_id}"



def _safe_get_user_id(event: Event) -> str | None:
    try:
        return event.get_user_id()
    except Exception:  # noqa: BLE001
        return None



def _safe_get_session_id(event: Event) -> str | None:
    try:
        return event.get_session_id()
    except Exception:  # noqa: BLE001
        return None



def _resolve_message_type(event: Event) -> str:
    message_type = getattr(event, "message_type", None)
    if isinstance(message_type, str) and message_type.strip():
        return message_type.strip()
    return "private"
