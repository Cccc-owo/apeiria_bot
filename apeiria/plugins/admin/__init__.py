"""Admin plugin — owner management commands."""

from pathlib import Path

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from apeiria.core.configs.models import PluginExtraData, PluginType
from apeiria.core.i18n import load_locales

require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")

# Register plugin locales
load_locales(Path(__file__).parent / "locales")

__plugin_meta__ = PluginMetadata(
    name="主人管理",
    description="主人专用的应急控制台：状态、群、插件、访问、任务、重启",
    usage=(
        "/admin - 查看总览\n"
        "/status | /sid - 查看运行与会话状态\n"
        "/group status|bot|plugin|access ... - 管理当前群\n"
        "/plugins | /plugin info|enable|disable|configs <插件名> - 管理插件\n"
        "/config core|plugin ... - 查看配置摘要\n"
        "/access plugin|rule|remove|level ... - 管理访问控制\n"
        "/tasks | /task info|pause|resume <任务ID> - 管理任务\n"
        "/restart - 重启 Bot\n"
        "/adapters | /drivers - 查看运行环境"
    ),
    type="application",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.SUPERUSER,
        admin_level=6,
        commands=[
            "admin",
            "status",
            "sid",
            "adapters",
            "drivers",
            "group",
            "plugins",
            "plugin",
            "config",
            "access",
            "restart",
            "tasks",
            "task",
        ],
        required_plugins=[
            "nonebot_plugin_alconna",
            "nonebot_plugin_orm",
            "nonebot_plugin_apscheduler",
        ],
    ).to_dict(),
)

from . import access_admin as access_admin
from . import adapters as adapters
from . import config_view as config_view
from . import drivers as drivers
from . import group_admin as group_admin
from . import overview as overview
from . import plugin_admin as plugin_admin
from . import restart as restart
from . import session_info as session_info
from . import status as status
from . import tasks as tasks
