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
    description="主人专用的系统管理命令：状态、插件、配置、任务、重启",
    usage=(
        "/status - 查看运行状态\n"
        "/sid - 查看当前会话 ID 信息\n"
        "/adapters - 查看适配器状态\n"
        "/drivers - 查看 driver 状态\n"
        "/plugins - 查看插件总览\n"
        "/plugin info <插件名> - 查看插件详情\n"
        "/plugin configs <插件名> - 查看插件配置摘要\n"
        "/plugin enable <插件名> - 启用插件\n"
        "/plugin disable <插件名> - 禁用插件\n"
        "/config core - 查看核心配置摘要\n"
        "/config plugin <插件名> - 查看插件配置摘要\n"
        "/restart - 重启 Bot\n"
        "/tasks - 查看调度任务\n"
        "/task info <任务ID> - 查看任务详情\n"
        "/task pause <任务ID> - 暂停任务\n"
        "/task resume <任务ID> - 恢复任务"
    ),
    type="application",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.SUPERUSER,
        admin_level=6,
        commands=[
            "status",
            "sid",
            "adapters",
            "drivers",
            "plugins",
            "plugin",
            "config",
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

from . import adapters as adapters
from . import config_view as config_view
from . import drivers as drivers
from . import plugin_admin as plugin_admin
from . import restart as restart
from . import session_info as session_info
from . import status as status
from . import tasks as tasks
