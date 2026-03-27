from __future__ import annotations

import locale
import os

MESSAGES_ZH_CN = {
    "Apeiria project tools.": "Apeiria 项目工具。",
    "Inspect and migrate Apeiria environments.": "查看并迁移 Apeiria 环境。",
    "Initialize Apeiria user environment with uv.": "使用 uv 初始化 Apeiria 用户环境。",
    "Repair Apeiria user environment with uv.": "使用 uv 修复 Apeiria 用户环境。",
    "Sync the main project environment without development dependencies.": (
        "同步主项目环境时不安装开发依赖。"
    ),
    "Run bot.py with the current project Python environment.": (
        "使用当前项目 Python 环境运行 bot.py。"
    ),
    "Show current Apeiria environment paths and status.": (
        "显示当前 Apeiria 环境路径和状态。"
    ),
    "Export local runtime state for migration.": "导出本地运行态以便迁移。",
    "Import local runtime state from a migration bundle.": ("从迁移包导入本地运行态。"),
    "Manage Apeiria project plugins.": "管理 Apeiria 项目插件。",
    "Manage Apeiria project adapters.": "管理 Apeiria 项目适配器。",
    "Manage Apeiria project drivers.": "管理 Apeiria 项目驱动。",
    "config: {path}": "配置文件：{path}",
    "modules:": "模块：",
    "dirs:": "目录：",
    "builtin:": "内建驱动：",
    "installed:": "已安装：",
    "registered:": "已登记：",
    "no installed plugin packages found": "未找到已安装的插件包",
    "no installed adapter packages found": "未找到已安装的适配器包",
    "no installed driver packages found": "未找到已安装的驱动包",
    "List registered plugin config only.": "仅列出已登记插件配置。",
    "List registered adapter config only.": "仅列出已登记适配器配置。",
    "Search registered plugin config only.": "仅搜索已登记插件配置。",
    "Search registered adapter config only.": "仅搜索已登记适配器配置。",
    "initialized: {target}": "已初始化：{target}",
    "initialized environment": "已初始化用户环境",
    "repaired environment": "已修复用户环境",
    "exported files: {count}": "已导出文件：{count}",
    "export target: {target}": "导出目标：{target}",
    "imported files: {count}": "已导入文件：{count}",
    "missing system dependencies: {deps}": "缺少系统依赖：{deps}",
    "frontend toolchain missing: {deps}": "缺少前端工具链：{deps}",
    "registered module: {module}": "已注册模块：{module}",
    "unregistered module: {module}": "已取消注册模块：{module}",
    "installed package: {package}": "已安装包：{package}",
    "updated package: {package}": "已更新包：{package}",
    "uninstalled package: {package}": "已卸载包：{package}",
    "added dir: {directory}": "已添加目录：{directory}",
    "removed dir: {directory}": "已移除目录：{directory}",
    "registered builtin: {builtin}": "已注册内建驱动：{builtin}",
    "unregistered builtin: {builtin}": "已取消注册内建驱动：{builtin}",
    "cannot remove protected plugin {module}: framework required": (
        "不能移除受保护插件 {module}：框架依赖"
    ),
    "--installed and --registered cannot be used together": (
        "--installed 和 --registered 不能同时使用"
    ),
    "Create apeiria.plugins.toml if it does not exist.": (
        "在 apeiria.plugins.toml 不存在时创建它。"
    ),
    "Create apeiria.plugins.toml and the user plugin project if missing.": (
        "在 apeiria.plugins.toml 或用户插件子项目不存在时创建它们。"
    ),
    "List registered plugins or installed plugin packages.": (
        "列出已登记插件或已安装插件包。"
    ),
    "List installed plugin packages.": "列出已安装插件包。",
    "Search registered plugins or installed plugin packages.": (
        "搜索已登记插件或已安装插件包。"
    ),
    "Search installed plugin packages.": "搜索已安装插件包。",
    "Register a plugin module in apeiria.plugins.toml.": (
        "在 apeiria.plugins.toml 中登记插件模块。"
    ),
    "Remove a plugin module from apeiria.plugins.toml.": (
        "从 apeiria.plugins.toml 中移除插件模块。"
    ),
    "Install a plugin package and optionally register its module.": (
        "安装插件包，并可选登记其模块。"
    ),
    "Install a plugin package.": "安装插件包。",
    "Module name to register.": "要登记的模块名。",
    "Install the package without registering it to apeiria.plugins.toml.": (
        "安装包但不写入 apeiria.plugins.toml。"
    ),
    "Update a plugin package with current environment manager.": (
        "使用当前环境管理器更新插件包。"
    ),
    "Uninstall a plugin package and optionally unregister its module.": (
        "卸载插件包，并可选取消登记其模块。"
    ),
    "Uninstall a plugin package.": "卸载插件包。",
    "Module name to unregister.": "要取消登记的模块名。",
    "Uninstall the package but keep the module registration.": (
        "卸载包，但保留模块登记。"
    ),
    "Register a plugin directory in apeiria.plugins.toml.": (
        "在 apeiria.plugins.toml 中登记插件目录。"
    ),
    "Remove a plugin directory from apeiria.plugins.toml.": (
        "从 apeiria.plugins.toml 中移除插件目录。"
    ),
    "Create apeiria.adapters.toml if it does not exist.": (
        "在 apeiria.adapters.toml 不存在时创建它。"
    ),
    "List registered adapters or installed adapter packages.": (
        "列出已登记适配器或已安装适配器包。"
    ),
    "List installed adapter packages.": "列出已安装适配器包。",
    "Search registered adapters or installed adapter packages.": (
        "搜索已登记适配器或已安装适配器包。"
    ),
    "Search installed adapter packages.": "搜索已安装适配器包。",
    "Open nonebot plugin store.": "打开 NoneBot 插件商店。",
    "Open nonebot adapter store.": "打开 NoneBot 适配器商店。",
    "Open nonebot driver store.": "打开 NoneBot 驱动商店。",
    "Browse nonebot plugin store with interactive selection.": (
        "以交互式选择方式浏览 NoneBot 插件商店。"
    ),
    "Browse nonebot adapter store with interactive selection.": (
        "以交互式选择方式浏览 NoneBot 适配器商店。"
    ),
    "Browse nonebot driver store with interactive selection.": (
        "以交互式选择方式浏览 NoneBot 驱动商店。"
    ),
    "List registered drivers or installed driver packages.": (
        "列出已登记驱动或已安装驱动包。"
    ),
    "List installed driver packages.": "列出已安装驱动包。",
    "List registered driver config only.": "仅列出已登记驱动配置。",
    "Search registered drivers or installed driver packages.": (
        "搜索已登记驱动或已安装驱动包。"
    ),
    "Search installed driver packages.": "搜索已安装驱动包。",
    "Search registered driver config only.": "仅搜索已登记驱动配置。",
    "List official store packages.": "列出官方商店资源。",
    "Search official store packages.": "搜索官方商店资源。",
    "Choose from official store.": "从官方商店中选择。",
    "store:": "官方商店：",
    "store choices:": "可选条目：",
    "store choices truncated": "候选过多，仅显示前 20 项",
    "choose package index": "请选择条目编号",
    "choose package": "请选择包",
    "no installed packages available": "当前没有可选择的已安装包",
    "no store packages found": "未找到可用的官方商店资源",
    "package name is required": "需要提供包名",
    "nb-cli is required for official store features": (
        "官方商店功能需要当前环境安装 nb-cli"
    ),
    "uv command failed": "uv 命令执行失败",
    "import source not found: {path}": "导入源不存在：{path}",
    "--installed, --registered and --store cannot be used together": (
        "--installed、--registered 和 --store 不能同时使用"
    ),
    "Register an adapter module in apeiria.adapters.toml.": (
        "在 apeiria.adapters.toml 中登记适配器模块。"
    ),
    "Remove an adapter module from apeiria.adapters.toml.": (
        "从 apeiria.adapters.toml 中移除适配器模块。"
    ),
    "Install an adapter package and optionally register its module.": (
        "安装适配器包，并可选登记其模块。"
    ),
    "Install an adapter package.": "安装适配器包。",
    "Install the package without registering it to apeiria.adapters.toml.": (
        "安装包但不写入 apeiria.adapters.toml。"
    ),
    "Update an adapter package with current environment manager.": (
        "使用当前环境管理器更新适配器包。"
    ),
    "Uninstall an adapter package and optionally unregister its module.": (
        "卸载适配器包，并可选取消登记其模块。"
    ),
    "Uninstall an adapter package.": "卸载适配器包。",
    "Create apeiria.drivers.toml if it does not exist.": (
        "在 apeiria.drivers.toml 不存在时创建它。"
    ),
    "Install a driver package.": "安装驱动包。",
    "Update a driver package with current environment manager.": (
        "使用当前环境管理器更新驱动包。"
    ),
    "Plugin module name to register when store metadata is unavailable.": (
        "当商店元数据不可用时，要登记的插件模块名。"
    ),
    "Adapter module name to register when store metadata is unavailable.": (
        "当商店元数据不可用时，要登记的适配器模块名。"
    ),
    "Driver builtin name to register when store metadata is unavailable.": (
        "当商店元数据不可用时，要登记的驱动 builtin 名。"
    ),
    "Plugin module name to unregister when package metadata is unavailable.": (
        "当包元数据不可用时，要取消登记的插件模块名。"
    ),
    "Adapter module name to unregister when package metadata is unavailable.": (
        "当包元数据不可用时，要取消登记的适配器模块名。"
    ),
    "Driver builtin name to unregister when package metadata is unavailable.": (
        "当包元数据不可用时，要取消登记的驱动 builtin 名。"
    ),
    "Install from a raw requirement string such as a git URL or local path.": (
        "从原始 requirement 字符串安装，例如 git URL 或本地路径。"
    ),
    "--store and --requirement cannot be used together": (
        "--store 和 --requirement 不能同时使用"
    ),
    "package name cannot be used with --requirement": (
        "使用 --requirement 时不能同时提供包名"
    ),
    "Choose which store source to use.": "选择要使用的商店源。",
    "unknown store source: {source}": "未知商店源：{source}",
    "requested module is not bound to package": "指定模块未绑定到该包",
    "requested builtin is not bound to package": "指定 builtin 未绑定到该包",
    "plugin module name is required when package is not from store": (
        "当包不来自官方商店时，需要通过 --module 指定插件模块名"
    ),
    "adapter module name is required when package is not from store": (
        "当包不来自官方商店时，需要通过 --module 指定适配器模块名"
    ),
    "driver builtin name is required when package is not from store": (
        "当包不来自官方商店时，需要通过 --builtin 指定驱动 builtin 名"
    ),
    "Uninstall a driver package.": "卸载驱动包。",
    "Register a built-in driver entry in apeiria.drivers.toml.": (
        "在 apeiria.drivers.toml 中登记内建驱动项。"
    ),
    "Remove a built-in driver entry from apeiria.drivers.toml.": (
        "从 apeiria.drivers.toml 中移除内建驱动项。"
    ),
    "Show effective NoneBot init kwargs generated from apeiria.drivers.toml.": (
        "显示由 apeiria.drivers.toml 生成的 NoneBot 初始化参数。"
    ),
}


def _env_locale() -> str | None:
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(key)
        if value and value.upper() != "C.UTF-8" and value.upper() != "C":
            return value
    return None


def get_locale() -> str | None:
    if env_locale := _env_locale():
        return env_locale
    current = locale.getlocale(locale.LC_MESSAGES)[0]
    if current:
        return current
    return locale.getlocale()[0]


def _(message: str) -> str:
    lang = get_locale() or ""
    if lang.lower().startswith("zh"):
        return MESSAGES_ZH_CN.get(message, message)
    return message
