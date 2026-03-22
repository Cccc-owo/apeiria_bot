"""Admin plugin — group management commands."""

from pathlib import Path

from nonebot.plugin import PluginMetadata

from apeiria.core.configs.models import PluginExtraData, PluginType
from apeiria.core.i18n import load_locales

# Register plugin locales
load_locales(Path(__file__).parent / "locales")

__plugin_meta__ = PluginMetadata(
    name="群管理",
    description="群组管理功能：封禁、禁言、踢出、插件开关、权限设置",
    usage=(
        "/ban @user [时长(分钟)] [原因] - 封禁用户\n"
        "/unban @user - 解除封禁\n"
        "/mute @user <时长(分钟)> - 禁言\n"
        "/unmute @user - 解除禁言\n"
        "/kick @user - 踢出群聊\n"
        "/enable <插件名> - 启用插件\n"
        "/disable <插件名> - 禁用插件\n"
        "/setlevel @user <等级> - 设置权限等级(0-4)\n"
        "/boton - 开启Bot\n"
        "/botoff - 关闭Bot\n"
        "/banlist - 查看封禁列表\n"
        "/pluginlist - 查看插件状态"
    ),
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.ADMIN,
        admin_level=5,
        commands=[
            "ban",
            "unban",
            "mute",
            "unmute",
            "kick",
            "enable",
            "disable",
            "setlevel",
            "boton",
            "botoff",
            "banlist",
            "pluginlist",
        ],
    ).to_dict(),
)

from . import ban as ban
from . import banlist as banlist
from . import bot_switch as bot_switch
from . import kick as kick
from . import mute as mute
from . import plugin_switch as plugin_switch
from . import pluginlist as pluginlist
from . import set_level as set_level
