"""Builtin AI plugin — conservative minimal chatbot entry."""

from pathlib import Path

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from apeiria.shared.i18n import load_locales, t
from apeiria.shared.plugin_metadata import (
    CommandDeclaration,
    ConfigExtra,
    HelpExtra,
    PluginExtraData,
    PluginType,
    RegisterConfig,
    UiExtra,
)

from .config import AIPluginConfig

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")

load_locales(Path(__file__).parent / "locales")

__plugin_meta__ = PluginMetadata(
    name=t("ai.meta.name"),
    description=t("ai.meta.description"),
    homepage="https://github.com/Cccc-owo/apeiria_bot",
    usage=t("ai.meta.usage"),
    type="application",
    config=AIPluginConfig,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.NORMAL,
        admin_level=0,
        help=HelpExtra(
            category=t("ai.meta.help_category"),
            introduction=t("ai.meta.help_introduction"),
        ),
        ui=UiExtra(order=30),
        commands=[
            CommandDeclaration(name="ai", description=t("ai.meta.command_ai")),
            CommandDeclaration(
                name="persona",
                description=t("ai.meta.command_persona"),
            ),
            CommandDeclaration(name="reset", description=t("ai.meta.command_reset")),
        ],
        config=ConfigExtra(
            fields=[
                RegisterConfig(
                    key="enabled",
                    default=True,
                    help=t("ai.meta.config_enabled"),
                    type=bool,
                ),
                RegisterConfig(
                    key="persona_prompt",
                    default="你是一个自然、克制、简洁的聊天伙伴。",
                    help=t("ai.meta.config_persona_prompt"),
                    type=str,
                ),
                RegisterConfig(
                    key="explicit_triggers",
                    default=[],
                    help=t("ai.meta.config_explicit_triggers"),
                    type=list,
                    item_type=str,
                ),
                RegisterConfig(
                    key="max_window_items",
                    default=5,
                    help=t("ai.meta.config_max_window_items"),
                    type=int,
                ),
                RegisterConfig(
                    key="error_reply_text",
                    default="",
                    help=t("ai.meta.config_error_reply_text"),
                    type=str,
                ),
            ]
        ),
        required_plugins=["nonebot_plugin_alconna", "nonebot_plugin_localstore"],
    ).to_dict(),
)

from . import commands as commands
from . import message_hook as message_hook
