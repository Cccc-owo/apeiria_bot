from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from apeiria.infra.config import project_config_service


class BuiltinPersona(BaseModel):
    name: str
    label: str
    prompt: str


class AIPluginConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    persona_prompt: str = "你是一个自然、克制、简洁的聊天伙伴。"
    explicit_triggers: list[str] = Field(default_factory=list)
    max_window_items: int = 5
    error_reply_text: str = ""


class AIModelSettings(BaseModel):
    enabled: bool = False
    provider: str = "openai_compatible"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 30.0


_DEFAULT_PERSONAS: tuple[BuiltinPersona, ...] = (
    BuiltinPersona(
        name="default",
        label="默认",
        prompt="你是一个自然、克制、简洁的聊天伙伴。",
    ),
    BuiltinPersona(
        name="gentle",
        label="温和",
        prompt="你说话温和、耐心、简洁，尽量让对方放松。",
    ),
    BuiltinPersona(
        name="cool",
        label="冷静",
        prompt="你说话冷静、利落、克制，少说空话。",
    ),
)


def get_ai_config() -> AIPluginConfig:
    config = project_config_service.read_project_plugin_config("ai")
    return AIPluginConfig.model_validate(config)


def get_builtin_personas() -> tuple[BuiltinPersona, ...]:
    return _DEFAULT_PERSONAS


def get_builtin_persona(name: str) -> BuiltinPersona | None:
    normalized = name.strip().lower()
    for persona in _DEFAULT_PERSONAS:
        if persona.name == normalized:
            return persona
    return None
