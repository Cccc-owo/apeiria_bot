from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from apeiria.config import project_config_service

ModelT = TypeVar("ModelT", bound=BaseModel)


class WebUIConfig(BaseModel):
    token_expire_days: int = 7


def _validate_config(model: type[ModelT], data: dict[str, object]) -> ModelT:
    if hasattr(model, "model_validate"):
        return model.model_validate(data)
    return model.parse_obj(data)


def get_web_ui_config() -> WebUIConfig:
    config = project_config_service.read_project_plugin_config("web_ui")
    if "token_expire_days" not in config:
        legacy = project_config_service.read_project_config()
        legacy_value = legacy.get("web_ui_token_expire_days")
        if legacy_value is not None:
            config["token_expire_days"] = legacy_value
    return _validate_config(WebUIConfig, config)
