from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from apeiria.user_config import read_project_config, read_project_plugin_config

ModelT = TypeVar("ModelT", bound=BaseModel)


class WebUIConfig(BaseModel):
    token_expire_days: int = 7


def _validate_config(model: type[ModelT], data: dict[str, object]) -> ModelT:
    if hasattr(model, "model_validate"):
        return model.model_validate(data)
    return model.parse_obj(data)


def get_web_ui_config() -> WebUIConfig:
    config = read_project_plugin_config("web_ui")
    if "token_expire_days" not in config:
        legacy = read_project_config()
        legacy_value = legacy.get("web_ui_token_expire_days")
        if legacy_value is not None:
            config["token_expire_days"] = legacy_value
    return _validate_config(WebUIConfig, config)
