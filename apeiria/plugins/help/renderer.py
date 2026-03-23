"""Render help data to images via HTMLKit."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from nonebot_plugin_htmlkit import html_to_pic

if TYPE_CHECKING:
    from .generator import PluginHelpInfo

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_RENDER_TIMEOUT = 3.0


async def _html_to_pic_with_timeout(html: str, *, max_width: int) -> bytes:
    return await asyncio.wait_for(
        html_to_pic(html, max_width=max_width),
        timeout=_RENDER_TIMEOUT,
    )


async def render_help_list(plugins: list[PluginHelpInfo]) -> bytes:
    """Render plugin list to a PNG image."""
    template = (_TEMPLATE_DIR / "help_list.html").read_text(encoding="utf-8")

    rows = ""
    for p in plugins:
        level_badge = ""
        if p.admin_level > 0:
            level_badge = (
                f'<span class="badge level-{p.admin_level}">Lv.{p.admin_level}</span>'
            )
        cmds = " ".join(f"<code>/{c}</code>" for c in p.commands) if p.commands else ""
        rows += (
            f"<tr>"
            f'<td class="name">{p.name} {level_badge}</td>'
            f'<td class="desc">{p.description}</td>'
            f'<td class="cmds">{cmds}</td>'
            f"</tr>"
        )

    html = template.replace("{{rows}}", rows).replace("{{count}}", str(len(plugins)))
    return await _html_to_pic_with_timeout(html, max_width=700)


async def render_plugin_detail(plugin: PluginHelpInfo) -> bytes:
    """Render single plugin detail to a PNG image."""
    template = (_TEMPLATE_DIR / "help_detail.html").read_text(encoding="utf-8")

    commands_html = ""
    if plugin.commands:
        items = "".join(f"<li><code>/{c}</code></li>" for c in plugin.commands)
        commands_html = f"<ul>{items}</ul>"

    usage_html = plugin.usage.replace("\n", "<br>") if plugin.usage else "暂无"

    html = (
        template.replace("{{name}}", plugin.name)
        .replace("{{description}}", plugin.description or "暂无描述")
        .replace("{{usage}}", usage_html)
        .replace("{{commands}}", commands_html or "暂无")
        .replace("{{version}}", plugin.version or "unknown")
        .replace("{{type}}", plugin.plugin_type)
        .replace("{{level}}", str(plugin.admin_level))
    )
    return await _html_to_pic_with_timeout(html, max_width=600)
