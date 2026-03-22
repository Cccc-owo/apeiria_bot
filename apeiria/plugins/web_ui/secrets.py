"""Web UI secrets — password and JWT token secret, persisted in data dir."""

from __future__ import annotations

import json
import secrets

from nonebot.log import logger
from nonebot_plugin_localstore import get_data_file

from apeiria.core.i18n import t

_PLUGIN_DATA_ID = "apeiria.plugins.web_ui"


def _load_or_create() -> dict[str, str]:
    """Load secrets from data dir, or generate and persist new ones."""
    secret_file = get_data_file(_PLUGIN_DATA_ID, "secret.json")

    if secret_file.is_file():
        try:
            data = json.loads(secret_file.read_text(encoding="utf-8"))
            if "password" in data and "token_secret" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass

    data = {
        "password": secrets.token_urlsafe(16),
        "token_secret": secrets.token_urlsafe(32),
    }
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("{}", t("web_ui.secrets.generated"))
    return data


_secrets = _load_or_create()


def get_password() -> str:
    return _secrets["password"]


def get_token_secret() -> str:
    return _secrets["token_secret"]
