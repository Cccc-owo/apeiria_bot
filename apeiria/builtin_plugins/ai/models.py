from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ChatMode = Literal["private", "group"]
RuleDecision = Literal["respond", "ignore"]


@dataclass(slots=True, frozen=True)
class SceneContext:
    chat_mode: ChatMode
    speaker_id: str
    speaker_name: str
    text: str
    is_mentioned: bool
    matched_trigger: str | None
    session_key: str


@dataclass(slots=True, frozen=True)
class PersonaSpec:
    name: str
    prompt: str
    label: str


@dataclass(slots=True, frozen=True)
class ChatTurn:
    speaker_id: str
    speaker_name: str
    user_text: str
    bot_reply: str | None = None


@dataclass(slots=True)
class SessionAIState:
    enabled: bool = True
    persona_name: str = "default"
    turns: list[ChatTurn] = field(default_factory=list)
