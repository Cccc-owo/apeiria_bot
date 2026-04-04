from __future__ import annotations

import json
from dataclasses import asdict

from nonebot.log import logger

from .models import ChatTurn, SessionAIState
from .storage import get_ai_window_state_file


class AIWindowStore:
    def __init__(self) -> None:
        self._state_file = get_ai_window_state_file()

    def load(self) -> dict[str, SessionAIState]:
        if not self._state_file.is_file():
            return {}
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to load AI plugin state from {}: {}",
                self._state_file,
                exc,
            )
            return {}

        states: dict[str, SessionAIState] = {}
        for session_key, raw in data.items():
            turns = [
                ChatTurn(**turn)
                for turn in raw.get("turns", [])
                if isinstance(turn, dict)
            ]
            states[session_key] = SessionAIState(
                enabled=bool(raw.get("enabled", True)),
                persona_name=str(raw.get("persona_name", "default") or "default"),
                turns=turns,
            )
        return states

    def save(self, states: dict[str, SessionAIState]) -> None:
        payload = {
            session_key: {
                "enabled": state.enabled,
                "persona_name": state.persona_name,
                "turns": [asdict(turn) for turn in state.turns],
            }
            for session_key, state in sorted(states.items())
        }
        temp_file = self._state_file.with_suffix(".tmp")
        temp_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_file.replace(self._state_file)


class AIWindowManager:
    def __init__(self, store: AIWindowStore | None = None) -> None:
        self.store = store or AIWindowStore()
        self._states = self.store.load()

    def get_state(self, session_key: str) -> SessionAIState:
        state = self._states.get(session_key)
        if state is None:
            state = SessionAIState()
            self._states[session_key] = state
        return state

    def set_enabled(self, session_key: str, *, enabled: bool) -> SessionAIState:
        state = self.get_state(session_key)
        state.enabled = enabled
        self.persist()
        return state

    def set_persona(self, session_key: str, persona_name: str) -> SessionAIState:
        state = self.get_state(session_key)
        state.persona_name = persona_name
        self.persist()
        return state

    def clear_turns(self, session_key: str) -> SessionAIState:
        state = self.get_state(session_key)
        state.turns = []
        self.persist()
        return state

    def append_turn(self, session_key: str, turn: ChatTurn, *, max_items: int) -> None:
        state = self.get_state(session_key)
        state.turns.append(turn)
        state.turns = state.turns[-max_items:]
        self.persist()

    def persist(self) -> None:
        self.store.save(self._states)


ai_window_manager = AIWindowManager()
