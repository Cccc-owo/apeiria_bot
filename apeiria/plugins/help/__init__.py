"""Help plugin — auto-generated command help system."""

from pathlib import Path

from nonebot.plugin import PluginMetadata

from apeiria.core.configs.models import PluginExtraData, PluginType
from apeiria.core.i18n import load_locales

# Register plugin locales
load_locales(Path(__file__).parent / "locales")

__plugin_meta__ = PluginMetadata(
    name="帮助系统",
    description="查看可用命令列表和插件详情",
    usage="/help - 查看所有命令\n/help <插件名> - 查看插件详情",
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.NORMAL,
        admin_level=0,
        commands=["help"],
    ).to_dict(),
)

from . import help_cmd as help_cmd
