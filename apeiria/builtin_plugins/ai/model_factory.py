from __future__ import annotations

from .model_base import (
    AIModelClient,
    UnconfiguredModelClient,
    get_model_settings,
)
from .model_openai import OpenAICompatibleModelClient


def get_model_client() -> AIModelClient:
    settings = get_model_settings()
    if settings.provider == "openai_compatible":
        return OpenAICompatibleModelClient(settings)
    return UnconfiguredModelClient()
