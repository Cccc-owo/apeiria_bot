from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .storage import load_ai_model_settings

if TYPE_CHECKING:
    from .config import AIModelSettings


class AIModelClient(Protocol):
    async def generate_text(self, prompt: str) -> str | None: ...


class UnconfiguredModelClient:
    async def generate_text(self, prompt: str) -> str | None:  # noqa: ARG002
        return None



def get_model_settings() -> AIModelSettings:
    return load_ai_model_settings()
