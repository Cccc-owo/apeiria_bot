from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, Field

from apeiria.infra.config import project_config_service

ModelT = TypeVar("ModelT", bound=BaseModel)


class PluginOverride(BaseModel):
    plugin_name: str = ""
    display_name: str = ""
    description: str = ""
    order: int = 99
    extra_commands: list[str] = Field(default_factory=list)


class CustomCategory(BaseModel):
    name: str = ""
    description: str = ""
    order: int = 99
    commands: list[str] = Field(default_factory=list)


class HelpConfig(BaseModel):
    title: str = "帮助菜单"
    subtitle: str = ""
    accent_color: str = "#4e96f7"
    show_builtin_cmds: bool = False
    plugin_blacklist: list[str] = Field(default_factory=list)
    admin_show_all: bool = False
    expand_commands: bool = False
    custom_templates: bool = False
    plugin_overrides: list[PluginOverride] = Field(default_factory=list)
    custom_categories: list[CustomCategory] = Field(default_factory=list)
    font_urls: list[str] = Field(default_factory=list)
    font_family: str = ""
    latin_font_family: str = ""
    mono_font_family: str = ""
    banner_image: str = ""
    header_logo: str = ""
    footer_text: str = ""
    disk_cache: bool = False
    debug: bool = False


def _validate_config(model: type[ModelT], data: dict[str, object]) -> ModelT:
    return model.model_validate(data)


def get_help_config() -> HelpConfig:
    config = project_config_service.read_project_plugin_config("help")
    return _validate_config(HelpConfig, config)
