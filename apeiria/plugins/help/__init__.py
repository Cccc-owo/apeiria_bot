"""Help plugin — auto-generated command help system."""

from pathlib import Path

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from apeiria.core.configs.models import PluginExtraData, PluginType, RegisterConfig
from apeiria.core.i18n import load_locales
from apeiria.plugins.help.config import HelpConfig

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("apeiria.plugins.render")

# Register plugin locales
load_locales(Path(__file__).parent / "locales")

__plugin_meta__ = PluginMetadata(
    name="帮助系统",
    description="图像化帮助菜单与插件详情",
    usage=(
        "/help - 查看帮助菜单\n"
        "/help <插件名> - 查看插件详情\n"
        "/help --all - 主人查看完整帮助\n"
        "/帮助 / /菜单 / /功能 - 帮助命令别名"
    ),
    type="application",
    config=HelpConfig,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.NORMAL,
        admin_level=0,
        commands=["help"],
        configs=[
            RegisterConfig(
                key="title",
                default="帮助菜单",
                help="Help menu title",
                type=str,
            ),
            RegisterConfig(
                key="subtitle",
                default="",
                help="Help menu subtitle",
                type=str,
            ),
            RegisterConfig(
                key="accent_color",
                default="#4e96f7",
                help="Accent color in hex",
                type=str,
            ),
            RegisterConfig(
                key="show_builtin_cmds",
                default=False,
                help="Show built-in and framework plugins",
                type=bool,
            ),
            RegisterConfig(
                key="plugin_blacklist",
                default=[],
                help="Plugin ids hidden from help menu",
                type=list,
                item_type=str,
            ),
            RegisterConfig(
                key="admin_show_all",
                default=False,
                help="Superusers always show complete help",
                type=bool,
            ),
            RegisterConfig(
                key="expand_commands",
                default=False,
                help="Show expanded menu instead of plugin cards",
                type=bool,
            ),
            RegisterConfig(
                key="custom_templates",
                default=False,
                help="Load templates from the plugin data directory first",
                type=bool,
            ),
            RegisterConfig(
                key="plugin_overrides",
                default=[],
                help="Plugin display overrides",
                type=list,
                item_type=dict,
            ),
            RegisterConfig(
                key="custom_categories",
                default=[],
                help="Custom command categories",
                type=list,
                item_type=dict,
            ),
            RegisterConfig(
                key="font_urls",
                default=[],
                help="Remote CSS URLs for custom fonts",
                type=list,
                item_type=str,
            ),
            RegisterConfig(
                key="font_family",
                default="",
                help="Primary CJK font family",
                type=str,
            ),
            RegisterConfig(
                key="latin_font_family",
                default="",
                help="Primary Latin font family",
                type=str,
            ),
            RegisterConfig(
                key="mono_font_family",
                default="",
                help="Monospace font family",
                type=str,
            ),
            RegisterConfig(
                key="banner_image",
                default="",
                help="Banner background image file in help data dir",
                type=str,
            ),
            RegisterConfig(
                key="header_logo",
                default="",
                help="Header logo file in help data dir",
                type=str,
            ),
            RegisterConfig(
                key="footer_text",
                default="",
                help="Footer text",
                type=str,
            ),
            RegisterConfig(
                key="disk_cache",
                default=False,
                help="Cache rendered images to disk",
                type=bool,
            ),
            RegisterConfig(
                key="debug",
                default=False,
                help="Enable debug logs for help rendering",
                type=bool,
            ),
        ],
        required_plugins=[
            "nonebot_plugin_alconna",
            "nonebot_plugin_localstore",
            "apeiria.plugins.render",
        ],
    ).to_dict(),
)

from . import help_cmd as help_cmd
