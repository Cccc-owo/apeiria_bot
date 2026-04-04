from .config import BuiltinPersona
from .models import ChatTurn, SceneContext

_SYSTEM_RULES = (
    "你是一个聊天机器人。"
    "不要因为收到消息就默认必须回应。"
    "如果你决定回应，请保持简短、自然、克制。"
    "不确定时不要编造，宁可保守表达。"
    "不要主动插话，不要长篇大论。"
)


def build_reply_prompt(
    *,
    scene: SceneContext,
    persona: BuiltinPersona,
    fallback_persona_prompt: str,
    turns: list[ChatTurn],
) -> str:
    persona_prompt = _resolve_persona_prompt(persona, fallback_persona_prompt)
    lines = [
        _SYSTEM_RULES,
        f"人格风格补充：{persona_prompt}",
        f"当前场景：{'群聊' if scene.chat_mode == 'group' else '私聊'}",
        f"当前发言者：{scene.speaker_name}",
    ]
    if turns:
        lines.extend(["最近相关对话：", _format_turns(turns)])
    lines.extend(["当前输入：", scene.text, "请直接给出简短回复。"])
    return "\n".join(lines)

def _format_turns(turns: list[ChatTurn]) -> str:
    lines: list[str] = []
    for turn in turns[-2:]:
        lines.append(f"{turn.speaker_name}: {turn.user_text}")
        if turn.bot_reply:
            lines.append(f"AI: {turn.bot_reply}")
    return "\n".join(lines)

def _resolve_persona_prompt(persona: BuiltinPersona, fallback_prompt: str) -> str:
    prompt = persona.prompt.strip()
    if prompt:
        return prompt
    return fallback_prompt.strip()
