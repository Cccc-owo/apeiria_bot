"""Render help menu data to images via the shared render plugin."""

from __future__ import annotations

import asyncio
import json
from hashlib import md5
from pathlib import Path
from typing import TYPE_CHECKING

from apeiria.plugins.help.utils import (
    build_default_logo_data_uri,
    get_cache_dir,
    get_template_dir,
    read_image_as_data_uri,
    resolve_data_file,
)
from apeiria.plugins.render import template_to_pic

if TYPE_CHECKING:
    from .config import HelpConfig
    from .generator import CommandHelpInfo, PluginHelpInfo

_MEMORY_CACHE: dict[str, bytes] = {}
_RENDER_LOCKS: dict[str, asyncio.Lock] = {}


async def render_help_menu(
    plugins: list[PluginHelpInfo],
    *,
    prefix: str,
    config: HelpConfig,
) -> bytes:
    """Render the main help menu to a PNG image."""
    template_name = "expanded_menu.html" if config.expand_commands else "main_menu.html"
    data = _build_main_menu_data(plugins, prefix=prefix, config=config)
    return await _render_with_cache(
        template_name,
        data,
        use_custom_templates=config.custom_templates,
        use_disk_cache=config.disk_cache,
    )


async def render_plugin_detail(
    plugin: PluginHelpInfo,
    *,
    prefix: str,
    config: HelpConfig,
) -> bytes:
    """Render one plugin detail page to a PNG image."""
    data = _build_sub_menu_data(plugin, prefix=prefix, config=config)
    return await _render_with_cache(
        "sub_menu.html",
        data,
        use_custom_templates=config.custom_templates,
        use_disk_cache=config.disk_cache,
    )


def _build_main_menu_data(
    plugins: list[PluginHelpInfo],
    *,
    prefix: str,
    config: HelpConfig,
) -> dict[str, object]:
    title = config.title or "帮助菜单"
    subtitle = config.subtitle or f"发送 {prefix}help <插件名> 查看详细命令"

    if config.expand_commands:
        plugin_data = [
            {
                "name": plugin.name,
                "display_name": plugin.display_name,
                "description": plugin.description,
                "icon_url": plugin.icon_url,
                "cmd_count": plugin.command_count,
                "commands": [
                    {
                        "display_name": _display_command_name(command, prefix),
                        "description": command.description,
                        "admin_only": command.admin_only,
                    }
                    for command in plugin.commands
                ],
            }
            for plugin in plugins
        ]
    else:
        plugin_data = [
            {
                "name": plugin.name,
                "display_name": plugin.display_name,
                "description": plugin.description,
                "icon_url": plugin.icon_url,
                "cmd_count": plugin.command_count,
            }
            for plugin in plugins
        ]

    return {
        "title": title,
        "subtitle": subtitle,
        "prefix": prefix,
        "plugin_total": len(plugins),
        "accent_color": _normalized_accent_color(config.accent_color),
        "banner_image": read_image_as_data_uri(resolve_data_file(config.banner_image)),
        "header_logo": _resolve_header_logo(config),
        "font_urls": [item for item in config.font_urls if item],
        "font_family": config.font_family.strip(),
        "latin_font_family": config.latin_font_family.strip(),
        "mono_font_family": config.mono_font_family.strip(),
        "plugins": plugin_data,
        "footer": _footer_text(config),
    }


def _build_sub_menu_data(
    plugin: PluginHelpInfo,
    *,
    prefix: str,
    config: HelpConfig,
) -> dict[str, object]:
    return {
        "plugin": {
            "name": plugin.name,
            "plugin_id": plugin.plugin_id,
            "module_name": plugin.module_name,
            "display_name": plugin.display_name,
            "description": plugin.description,
            "icon_url": plugin.icon_url,
        },
        "commands": [
            {
                "display_name": _display_command_name(command, prefix),
                "description": command.description,
                "aliases": [
                    _display_alias(alias, command.custom_prefix, prefix)
                    for alias in command.aliases
                ],
                "usage": command.usage,
                "admin_only": command.admin_only,
            }
            for command in plugin.commands
        ],
        "command_count": len(plugin.commands),
        "prefix": prefix,
        "accent_color": _normalized_accent_color(config.accent_color),
        "font_urls": [item for item in config.font_urls if item],
        "font_family": config.font_family.strip(),
        "latin_font_family": config.latin_font_family.strip(),
        "mono_font_family": config.mono_font_family.strip(),
        "footer": _footer_text(config),
    }


async def _render_with_cache(
    template_name: str,
    data: dict[str, object],
    *,
    use_custom_templates: bool,
    use_disk_cache: bool,
) -> bytes:
    template_dir, render_options, key = _resolve_render_cache_context(
        template_name,
        data,
        use_custom_templates=use_custom_templates,
    )
    cache_file = get_cache_dir() / f"{key}.png"

    if use_disk_cache and cache_file.is_file():
        content = cache_file.read_bytes()
        if content:
            return content
    if not use_disk_cache:
        cached = _MEMORY_CACHE.get(key)
        if cached is not None:
            return cached

    lock = _RENDER_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        if use_disk_cache and cache_file.is_file():
            content = cache_file.read_bytes()
            if content:
                return content
        if not use_disk_cache:
            cached = _MEMORY_CACHE.get(key)
            if cached is not None:
                return cached

        rendered = await template_to_pic(
            template_name,
            context=data,
            template_dir=template_dir,
            width=render_options["width"],
            timeout_ms=render_options["timeout_ms"],
            wait_until=render_options["wait_until"],
            selector=render_options["selector"],
        )

        if use_disk_cache:
            cache_file.write_bytes(rendered)
        else:
            _MEMORY_CACHE[key] = rendered
        return rendered


def _cache_key(
    template_name: str,
    data: dict[str, object],
    *,
    template_dir: Path,
    render_options: dict[str, object],
) -> str:
    try:
        template_path = Path(template_dir) / template_name
        template_source = template_path.read_text(encoding="utf-8")
    except OSError:
        template_source = ""
    payload = json.dumps(
        {
            "template": template_name,
            "template_source": template_source,
            "render_options": render_options,
            "data": data,
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return md5(payload).hexdigest()


def build_render_cache_key(
    template_name: str,
    data: dict[str, object],
    *,
    use_custom_templates: bool,
) -> str:
    """Build the disk cache key for one help render payload."""

    _, _, key = _resolve_render_cache_context(
        template_name,
        data,
        use_custom_templates=use_custom_templates,
    )
    return key


def cleanup_stale_disk_cache(valid_keys: set[str]) -> int:
    """Remove help disk cache files that are no longer valid."""

    cache_dir = get_cache_dir()
    removed = 0
    for cache_file in cache_dir.glob("*.png"):
        try:
            if cache_file.stem in valid_keys:
                continue
            cache_file.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def _resolve_render_cache_context(
    template_name: str,
    data: dict[str, object],
    *,
    use_custom_templates: bool,
) -> tuple[Path, dict[str, object], str]:
    template_dir = get_template_dir(
        template_name,
        use_custom=use_custom_templates,
    )
    selector = ".shell" if template_name != "sub_menu.html" else "body"
    render_options = {
        "selector": selector,
        "width": 960,
        "timeout_ms": 12_000,
        "wait_until": "networkidle",
    }
    key = _cache_key(
        template_name,
        data,
        template_dir=template_dir,
        render_options=render_options,
    )
    return template_dir, render_options, key


def _display_command_name(command: CommandHelpInfo, prefix: str) -> str:
    effective_prefix = (
        prefix if command.custom_prefix is None else command.custom_prefix
    )
    return f"{effective_prefix}{command.name}"


def _display_alias(alias: str, custom_prefix: str | None, prefix: str) -> str:
    effective_prefix = prefix if custom_prefix is None else custom_prefix
    return f"{effective_prefix}{alias}"


def _resolve_header_logo(config: HelpConfig) -> str:
    custom_logo = read_image_as_data_uri(resolve_data_file(config.header_logo))
    if custom_logo:
        return custom_logo
    return build_default_logo_data_uri()


def _footer_text(config: HelpConfig) -> str:
    if config.footer_text.strip():
        return config.footer_text.strip()
    return "Apeiria"


def _normalized_accent_color(color: str) -> str:
    stripped = color.strip()
    if stripped.startswith("#") and len(stripped) in {4, 7}:
        return stripped
    return "#4e96f7"
