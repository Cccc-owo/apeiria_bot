"""Global bot configuration, extending nonebot2 config."""

from __future__ import annotations

import nonebot
from pydantic import BaseModel

from apeiria.core.i18n import t


class BotConfig(BaseModel):
    """Extended bot configuration.

    Loaded via nonebot.get_plugin_config(BotConfig).
    Values can be set in .env / .env.dev / .env.prod files.
    """

    # Error handling
    error_message: str = "common.error"

    # Web UI
    web_ui_token_expire_days: int = 7

    # Rate limiting (default: per-user per-command)
    rate_limit_default: int = 5  # Max calls per window
    rate_limit_window: int = 60  # Window in seconds

    # Logging
    log_rotation: str = "00:00"  # Daily rotation
    log_retention: str = "30 days"


bot_config = nonebot.get_plugin_config(BotConfig)


def get_error_message() -> str:
    """Resolve configured error message, supporting either i18n key or raw text."""
    message = bot_config.error_message
    return t(message) if "." in message else message
