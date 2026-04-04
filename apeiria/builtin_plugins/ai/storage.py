from __future__ import annotations

import json
from typing import TYPE_CHECKING

import nonebot
from nonebot.log import logger

from apeiria.infra.config import project_config_service
from apeiria.shared.files import atomic_write_text

from .config import AIModelSettings

if TYPE_CHECKING:
    from pathlib import Path


def get_ai_data_dir() -> Path:
    _ensure_nonebot_initialized()

    from nonebot_plugin_localstore import get_data_file

    data_dir = get_data_file("ai", ".keep").parent
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_ai_window_state_file() -> Path:
    return get_ai_data_dir() / "state.json"


def get_ai_model_settings_file() -> Path:
    return get_ai_data_dir() / "model.json"


def load_ai_model_settings() -> AIModelSettings:
    path = get_ai_model_settings_file()
    if not path.is_file():
        settings = AIModelSettings()
        save_ai_model_settings(settings)
        return settings

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load AI model settings from {}: {}", path, exc)
        return AIModelSettings()

    if not isinstance(payload, dict):
        logger.warning("AI model settings file {} has unsupported schema", path)
        return AIModelSettings()
    return AIModelSettings.model_validate(payload)


def save_ai_model_settings(settings: AIModelSettings) -> None:
    path = get_ai_model_settings_file()
    atomic_write_text(
        path,
        json.dumps(
            settings.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )


def _ensure_nonebot_initialized() -> None:
    try:
        nonebot.get_driver()
    except ValueError:
        nonebot.init(**project_config_service.get_project_config_kwargs())
