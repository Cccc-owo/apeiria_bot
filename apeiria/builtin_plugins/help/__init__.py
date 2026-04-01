"""Help plugin — auto-generated command help system."""

from pathlib import Path

from nonebot import get_driver, require
from nonebot.log import logger
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from apeiria.builtin_plugins.help.config import (
    HelpConfig,
    get_help_config,
)
from apeiria.builtin_plugins.help.generator import (
    generate_help_list,
    get_command_prefix,
)
from apeiria.builtin_plugins.help.renderer import (
    _build_main_menu_data,
    _build_sub_menu_data,
    build_render_cache_key,
    cleanup_stale_disk_cache,
)
from apeiria.shared.i18n import load_locales
from apeiria.shared.plugin_metadata import (
    ConfigExtra,
    HelpExtra,
    PluginExtraData,
    PluginType,
    RegisterConfig,
    UiExtra,
)

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("apeiria.builtin_plugins.render")

# Register plugin locales
load_locales(Path(__file__).parent / "locales")


def _config_meta(  # noqa: PLR0913
    key: str,
    *,
    label: str = "",
    help_text: str = "",
    order: int = 99,
    fields: list[RegisterConfig] | None = None,
    item_schema: RegisterConfig | None = None,
    choices: list[object] | None = None,
    choice_labels: dict[str, str] | None = None,
) -> RegisterConfig:
    return RegisterConfig(
        key=key,
        default=None,
        type=str,
        label=label,
        help=help_text,
        order=order,
        fields=list(fields or []),
        item_schema=item_schema,
        choices=list(choices or []),
        choice_labels=dict(choice_labels or {}),
    )


def _cleanup_help_disk_cache() -> None:
    config = get_help_config()
    if not config.disk_cache:
        return

    prefix = get_command_prefix()
    valid_keys: set[str] = set()
    for show_all in (False, True):
        for role in ("user", "admin", "owner"):
            plugins = generate_help_list(config, role=role, show_all=show_all)
            template_name = (
                "expanded_menu.html" if config.expand_commands else "main_menu.html"
            )
            main_data = _build_main_menu_data(
                plugins,
                prefix=prefix,
                config=config,
                role=role,
            )
            valid_keys.add(
                build_render_cache_key(
                    template_name,
                    main_data,
                    use_custom_templates=config.custom_templates,
                )
            )
            for plugin in plugins:
                detail_data = _build_sub_menu_data(
                    plugin,
                    prefix=prefix,
                    config=config,
                    role=role,
                )
                valid_keys.add(
                    build_render_cache_key(
                        "sub_menu.html",
                        detail_data,
                        use_custom_templates=config.custom_templates,
                    )
                )

    removed = cleanup_stale_disk_cache(valid_keys)
    if removed > 0:
        logger.info("Removed {} stale help cache file(s)", removed)


__plugin_meta__ = PluginMetadata(
    name="帮助系统",
    description="图像化帮助菜单与插件详情",
    homepage="https://github.com/Cccc-owo/apeiria_bot",
    usage=(
        "/help - 查看帮助菜单\n"
        "/help <插件名> - 查看插件详情\n"
        "/help --admin - 查看管理视图帮助\n"
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
        help=HelpExtra(
            category="帮助与菜单",
            introduction="统一展示插件功能、命令与说明的帮助系统。",
        ),
        ui=UiExtra(order=5),
        commands=["help"],
        config=ConfigExtra(
            fields=[
                _config_meta(
                    key="appearance",
                    label="菜单外观",
                    order=10,
                    help_text="控制帮助菜单的标题、主色和展示样式。",
                    fields=[
                        _config_meta(
                            key="title",
                            label="菜单标题",
                            order=10,
                            help_text="显示在帮助菜单顶部的主标题。",
                        ),
                        _config_meta(
                            key="subtitle",
                            label="副标题",
                            order=20,
                            help_text="显示在标题下方的补充说明，可留空。",
                        ),
                        _config_meta(
                            key="accent_color",
                            label="主色",
                            order=30,
                            help_text=(
                                "帮助菜单的主题色，使用十六进制颜色值，"
                                "例如 #4e96f7。"
                            ),
                        ),
                        _config_meta(
                            key="expand_commands",
                            label="直接展开命令列表",
                            order=40,
                            help_text="开启后直接展示命令列表，不再按插件卡片分组。",
                        ),
                    ],
                ),
                _config_meta(
                    key="visibility",
                    label="显示范围",
                    order=20,
                    help_text="控制哪些插件会出现在帮助菜单中。",
                    fields=[
                        _config_meta(
                            key="show_builtin_plugins",
                            label="显示内置插件",
                            order=10,
                            help_text="显示框架和内置插件；关闭后只展示常规业务插件。",
                        ),
                        _config_meta(
                            key="hidden_plugins",
                            label="隐藏插件",
                            order=20,
                            help_text=(
                                "这些插件不会出现在帮助菜单中。"
                                "直接填写插件模块名，例如 "
                                "apeiria.builtin_plugins.help。"
                            ),
                        ),
                    ],
                ),
                _config_meta(
                    key="roles",
                    label="身份视图",
                    order=30,
                    help_text="按普通用户、管理员、主人展示不同的帮助菜单。",
                    fields=[
                        _config_meta(
                            key="enabled",
                            label="启用身份区分",
                            order=10,
                            help_text="根据当前身份展示不同内容的帮助菜单。",
                        ),
                        _config_meta(
                            key="mode",
                            label="切换方式",
                            order=20,
                            help_text=(
                                "选“自动切换”时，会按当前身份自动显示对应菜单；"
                                "选“仅手动切换”时，只有使用 --admin 等参数才切换。"
                            ),
                            choices=["auto", "manual_only"],
                            choice_labels={
                                "auto": "自动切换",
                                "manual_only": "仅手动切换",
                            },
                        ),
                        _config_meta(
                            key="owner_sees_all",
                            label="主人默认显示全部",
                            order=30,
                            help_text=(
                                "开启后，主人默认看到完整帮助列表，"
                                "无需额外使用 --all。"
                            ),
                        ),
                        _config_meta(
                            key="user_title",
                            label="普通用户标题",
                            order=40,
                            help_text="普通用户视图的标题覆盖文案，留空则使用统一标题。",
                        ),
                        _config_meta(
                            key="admin_title",
                            label="管理员标题",
                            order=50,
                            help_text="管理员视图的标题覆盖文案，留空则使用统一标题。",
                        ),
                        _config_meta(
                            key="owner_title",
                            label="主人标题",
                            order=60,
                            help_text="主人视图的标题覆盖文案，留空则使用统一标题。",
                        ),
                    ],
                ),
                _config_meta(
                    key="assets",
                    label="资源与品牌",
                    order=40,
                    help_text="配置菜单横幅、Logo、页脚和字体。",
                    fields=[
                        _config_meta(
                            key="banner_image",
                            label="横幅背景图",
                            order=10,
                            help_text=(
                                "填写帮助数据目录中的图片文件名，例如 banner.png；"
                                "留空则使用默认背景。"
                            ),
                        ),
                        _config_meta(
                            key="header_logo",
                            label="顶部 Logo",
                            order=20,
                            help_text=(
                                "填写帮助数据目录中的 Logo 文件名，例如 logo.png；"
                                "留空则不显示。"
                            ),
                        ),
                        _config_meta(
                            key="footer_text",
                            label="页脚文案",
                            order=30,
                            help_text="显示在菜单底部的补充文案。",
                        ),
                        _config_meta(
                            key="font_urls",
                            label="远程字体样式表",
                            order=40,
                            help_text=(
                                "填写字体 CSS 地址列表，例如 "
                                "https://example.com/font.css；通常无需修改。"
                            ),
                        ),
                        _config_meta(
                            key="font_family",
                            label="主字体",
                            order=50,
                            help_text="主要中文字体名称，通常保持默认即可。",
                        ),
                        _config_meta(
                            key="latin_font_family",
                            label="西文字体",
                            order=60,
                            help_text="英文和数字使用的字体名称，通常无需修改。",
                        ),
                        _config_meta(
                            key="mono_font_family",
                            label="等宽字体",
                            order=70,
                            help_text="命令和代码文本使用的字体名称，通常无需修改。",
                        ),
                    ],
                ),
                _config_meta(
                    key="render",
                    label="渲染与缓存",
                    order=90,
                    help_text="模板加载、缓存和调试等高级选项。",
                    fields=[
                        _config_meta(
                            key="prefer_custom_templates",
                            label="优先使用自定义模板",
                            order=10,
                            help_text="优先从插件数据目录加载模板，适合自定义样式时使用。",
                        ),
                        _config_meta(
                            key="disk_cache",
                            label="启用磁盘缓存",
                            order=20,
                            help_text="将渲染结果缓存到磁盘，减少重复渲染开销。",
                        ),
                        _config_meta(
                            key="debug",
                            label="输出调试日志",
                            order=30,
                            help_text="输出帮助渲染的调试日志，仅排查问题时开启。",
                        ),
                    ],
                ),
                _config_meta(
                    key="plugin_overrides",
                    label="插件展示覆盖",
                    order=100,
                    help_text=(
                        "为缺少完整元数据的插件手动补充展示名称、描述、"
                        "分类标签、排序和命令。"
                    ),
                    item_schema=_config_meta(
                        key="override",
                        label="插件覆盖项",
                        help_text="每一项对应一个要手动补充说明的插件。",
                        fields=[
                            _config_meta(
                                key="plugin_name",
                                label="插件标识",
                                order=10,
                                help_text=(
                                    "填写要补充说明的插件模块名，"
                                    "例如 nonebot_plugin_status。"
                                ),
                            ),
                            _config_meta(
                                key="display_name",
                                label="展示名称",
                                order=20,
                                help_text="覆盖插件在帮助菜单中的显示名称。",
                            ),
                            _config_meta(
                                key="description",
                                label="展示描述",
                                order=30,
                                help_text="覆盖插件在帮助菜单中的描述。",
                            ),
                            _config_meta(
                                key="category",
                                label="分类标签",
                                order=40,
                                help_text="给这个插件加一个展示标签，例如 系统工具。",
                            ),
                            _config_meta(
                                key="order",
                                label="排序",
                                order=50,
                                help_text="数值越小越靠前。",
                            ),
                            _config_meta(
                                key="extra_commands",
                                label="补充命令",
                                order=60,
                                help_text=(
                                    "额外追加到该插件卡片中的命令列表。"
                                    "每一项写成 命令名|描述|前缀，例如 "
                                    "status|查看运行状态|/。"
                                ),
                            ),
                        ],
                    ),
                ),
            ]
        ),
        required_plugins=[
            "nonebot_plugin_alconna",
            "nonebot_plugin_localstore",
            "apeiria.builtin_plugins.render",
        ],
    ).to_dict(),
)

from . import help_cmd as help_cmd

get_driver().on_startup(_cleanup_help_disk_cache)
