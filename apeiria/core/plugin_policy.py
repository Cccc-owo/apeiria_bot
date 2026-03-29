from __future__ import annotations

FRAMEWORK_PROTECTED_PLUGIN_MODULES = frozenset(
    {
        "apeiria.plugins.admin",
        "apeiria.plugins.help",
        "apeiria.plugins.web_ui",
        "apeiria.plugins.render",
        "nonebot_plugin_apscheduler",
        "nonebot_plugin_localstore",
        "nonebot_plugin_orm",
        "nonebot_plugin_alconna",
        "nonebot_plugin_alconna.uniseg",
        "nonebot_plugin_waiter",
    }
)


def is_framework_protected_plugin_module(module_name: str) -> bool:
    return module_name in FRAMEWORK_PROTECTED_PLUGIN_MODULES
