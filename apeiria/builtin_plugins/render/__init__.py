"""Playwright-based shared renderer service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from markdown_it import MarkdownIt
from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from apeiria.shared.plugin_metadata import (
    ConfigExtra,
    PluginExtraData,
    PluginType,
    RegisterConfig,
    UiExtra,
)

from .config import RenderConfig, get_render_config
from .service import (
    RenderOptions,
    RenderService,
    RenderServiceStatus,
    RenderUnavailableError,
    is_playwright_available,
    playwright_dependency_message,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

__plugin_meta__ = PluginMetadata(
    name="统一渲染服务",
    description="基于 Playwright 的统一 HTML 截图渲染服务",
    homepage="https://github.com/Cccc-owo/apeiria_bot",
    usage=(
        "供官方插件调用的基础设施插件。\n"
        "默认无聊天命令，提供 render_html / render_template / render_url API，"
        "以及 html_to_pic / template_to_pic / url_to_pic / markdown_to_pic "
        "兼容风格别名。"
    ),
    type="library",
    config=RenderConfig,
    supported_adapters=None,
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.HIDDEN,
        admin_level=0,
        ui=UiExtra(order=20, hidden=True),
        config=ConfigExtra(
            fields=[
                RegisterConfig(
                    key="headless",
                    default=True,
                    help="Launch Playwright Chromium in headless mode",
                    type=bool,
                ),
                RegisterConfig(
                    key="channel",
                    default="",
                    help="Browser channel name such as chrome or msedge",
                    type=str,
                ),
                RegisterConfig(
                    key="executable_path",
                    default="",
                    help="Custom browser executable path",
                    type=str,
                ),
                RegisterConfig(
                    key="launch_args",
                    default=[],
                    help="Extra browser launch arguments",
                    type=list,
                    item_type=str,
                ),
                RegisterConfig(
                    key="browser_locale",
                    default="zh-CN",
                    help="Default browser locale for rendered pages",
                    type=str,
                ),
                RegisterConfig(
                    key="user_agent",
                    default="",
                    help="Optional shared user agent for rendering contexts",
                    type=str,
                ),
                RegisterConfig(
                    key="default_width",
                    default=960,
                    help="Default viewport width",
                    type=int,
                ),
                RegisterConfig(
                    key="default_height",
                    default=540,
                    help="Default viewport height",
                    type=int,
                ),
                RegisterConfig(
                    key="default_device_scale_factor",
                    default=2.0,
                    help="Default device scale factor",
                    type=float,
                ),
                RegisterConfig(
                    key="default_timeout_ms",
                    default=15000,
                    help="Default render timeout in milliseconds",
                    type=int,
                ),
                RegisterConfig(
                    key="max_concurrency",
                    default=2,
                    help="Maximum concurrent render tasks",
                    type=int,
                ),
                RegisterConfig(
                    key="startup_warmup",
                    default=True,
                    help="Start browser warmup asynchronously during startup",
                    type=bool,
                ),
            ]
        ),
    ).to_dict(),
)

_service = RenderService(get_render_config())
_markdown = MarkdownIt("commonmark", {"breaks": True, "html": False}).enable("table")
_DEFAULT_MARKDOWN_STYLE = """
body {
  margin: 0;
  background: #0b0e14;
  color: #e6edf3;
  font-family: "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
}

.markdown-body {
  width: 100%;
  padding: 28px 30px;
  line-height: 1.7;
  font-size: 16px;
  color: #e6edf3;
}

.markdown-body > *:first-child { margin-top: 0; }
.markdown-body > *:last-child { margin-bottom: 0; }

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  margin: 1.2em 0 0.55em;
  line-height: 1.35;
  font-weight: 800;
  color: #f7fbff;
}

.markdown-body h1 { font-size: 2em; }
.markdown-body h2 { font-size: 1.6em; }
.markdown-body h3 { font-size: 1.3em; }

.markdown-body p,
.markdown-body ul,
.markdown-body ol,
.markdown-body blockquote,
.markdown-body pre,
.markdown-body table {
  margin: 0 0 1em;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 1.5em;
}

.markdown-body li + li {
  margin-top: 0.25em;
}

.markdown-body a {
  color: #72b4ff;
  text-decoration: none;
}

.markdown-body code {
  padding: 0.16em 0.38em;
  border-radius: 6px;
  background: rgba(110, 118, 129, 0.22);
  color: #c9d1d9;
  font-family: "JetBrains Mono", "Noto Sans Mono", "Consolas", monospace;
  font-size: 0.92em;
}

.markdown-body pre {
  overflow: hidden;
  padding: 14px 16px;
  border-radius: 12px;
  background: #161b22;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.markdown-body pre code {
  padding: 0;
  background: transparent;
}

.markdown-body blockquote {
  padding: 0.2em 1em;
  color: rgba(230, 237, 243, 0.76);
  border-left: 4px solid #4e96f7;
  background: rgba(78, 150, 247, 0.08);
  border-radius: 0 10px 10px 0;
}

.markdown-body hr {
  margin: 1.5em 0;
  border: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.markdown-body table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 12px;
  border-style: hidden;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.markdown-body th,
.markdown-body td {
  padding: 10px 12px;
  text-align: left;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.markdown-body th {
  background: rgba(78, 150, 247, 0.14);
  color: #f7fbff;
  font-weight: 700;
}

.markdown-body tr:nth-child(even) td {
  background: rgba(255, 255, 255, 0.02);
}

.markdown-body img {
  display: block;
  max-width: 100%;
  border-radius: 12px;
}
""".strip()


def _normalized_wait_until(value: str) -> str:
    allowed = {"commit", "domcontentloaded", "load", "networkidle"}
    normalized = value.strip().lower()
    if normalized in allowed:
        return normalized
    return "networkidle"


def _build_options(  # noqa: PLR0913
    *,
    width: int | None = None,
    height: int | None = None,
    max_width: int | None = None,
    timeout_ms: int | None = None,
    wait_until: str = "networkidle",
    selector: str | None = None,
    full_page: bool = False,
    device_scale_factor: float | None = None,
    css_urls: Sequence[str] | None = None,
    inline_style: str = "",
    extra_head_html: str = "",
    base_url: str = "",
    settle_time_ms: int = 0,
) -> RenderOptions:
    return RenderOptions(
        width=max_width or width,
        height=height,
        timeout_ms=timeout_ms,
        wait_until=_normalized_wait_until(wait_until),  # type: ignore[arg-type]
        selector=selector,
        full_page=full_page,
        device_scale_factor=device_scale_factor,
        css_urls=list(css_urls or ()),
        inline_style=inline_style,
        extra_head_html=extra_head_html,
        base_url=base_url,
        settle_time_ms=settle_time_ms,
    )


async def render_html(
    html: str,
    *,
    options: RenderOptions | None = None,
) -> bytes:
    """Render HTML content to an image."""
    return await _service.render_html(html, options=options)


async def render_url(
    url: str,
    *,
    options: RenderOptions | None = None,
) -> bytes:
    """Render one URL to an image."""
    return await _service.render_url(url, options=options)


async def render_template(
    template_name: str,
    *,
    context: dict[str, Any] | None = None,
    template_dir: str | Path,
    options: RenderOptions | None = None,
) -> bytes:
    """Render one Jinja template file to an image."""
    return await _service.render_template(
        template_name,
        context=context,
        template_dir=template_dir,
        options=options,
    )


async def html_to_pic(  # noqa: PLR0913
    html: str,
    *,
    width: int | None = None,
    height: int | None = None,
    max_width: int | None = None,
    timeout_ms: int | None = None,
    wait_until: str = "networkidle",
    selector: str | None = None,
    full_page: bool = False,
    device_scale_factor: float | None = None,
    css_urls: Sequence[str] | None = None,
    inline_style: str = "",
    extra_head_html: str = "",
    base_url: str = "",
    settle_time_ms: int = 0,
) -> bytes:
    """Render HTML to an image with a htmlkit-like convenience API."""
    options = _build_options(
        width=width,
        height=height,
        max_width=max_width,
        timeout_ms=timeout_ms,
        wait_until=wait_until,
        selector=selector,
        full_page=full_page,
        device_scale_factor=device_scale_factor,
        css_urls=css_urls,
        inline_style=inline_style,
        extra_head_html=extra_head_html,
        base_url=base_url,
        settle_time_ms=settle_time_ms,
    )
    return await render_html(html, options=options)


async def template_to_pic(  # noqa: PLR0913
    template_name: str,
    *,
    template_dir: str | Path,
    context: dict[str, Any] | None = None,
    width: int | None = None,
    height: int | None = None,
    max_width: int | None = None,
    timeout_ms: int | None = None,
    wait_until: str = "networkidle",
    selector: str | None = None,
    full_page: bool = False,
    device_scale_factor: float | None = None,
    css_urls: Sequence[str] | None = None,
    inline_style: str = "",
    extra_head_html: str = "",
    base_url: str = "",
    settle_time_ms: int = 0,
) -> bytes:
    """Render a Jinja template to an image with a convenience API."""
    options = _build_options(
        width=width,
        height=height,
        max_width=max_width,
        timeout_ms=timeout_ms,
        wait_until=wait_until,
        selector=selector,
        full_page=full_page,
        device_scale_factor=device_scale_factor,
        css_urls=css_urls,
        inline_style=inline_style,
        extra_head_html=extra_head_html,
        base_url=base_url,
        settle_time_ms=settle_time_ms,
    )
    return await render_template(
        template_name,
        context=context,
        template_dir=template_dir,
        options=options,
    )


async def url_to_pic(  # noqa: PLR0913
    url: str,
    *,
    width: int | None = None,
    height: int | None = None,
    timeout_ms: int | None = None,
    wait_until: str = "networkidle",
    selector: str | None = None,
    full_page: bool = False,
    device_scale_factor: float | None = None,
    settle_time_ms: int = 0,
) -> bytes:
    """Render a URL to an image with a convenience API."""
    options = _build_options(
        width=width,
        height=height,
        timeout_ms=timeout_ms,
        wait_until=wait_until,
        selector=selector,
        full_page=full_page,
        device_scale_factor=device_scale_factor,
        settle_time_ms=settle_time_ms,
    )
    return await render_url(url, options=options)


async def markdown_to_pic(  # noqa: PLR0913
    markdown: str,
    *,
    width: int | None = None,
    height: int | None = None,
    max_width: int | None = None,
    timeout_ms: int | None = None,
    wait_until: str = "networkidle",
    selector: str | None = ".markdown-body",
    full_page: bool = False,
    device_scale_factor: float | None = None,
    css_urls: Sequence[str] | None = None,
    inline_style: str = "",
    extra_head_html: str = "",
    base_url: str = "",
    settle_time_ms: int = 0,
) -> bytes:
    """Render Markdown content to an image with a built-in readable stylesheet."""
    html = _markdown.render(markdown)
    merged_style = _DEFAULT_MARKDOWN_STYLE
    if inline_style.strip():
        merged_style = f"{_DEFAULT_MARKDOWN_STYLE}\n\n{inline_style.strip()}"
    return await html_to_pic(
        f'<article class="markdown-body">{html}</article>',
        width=width,
        height=height,
        max_width=max_width,
        timeout_ms=timeout_ms,
        wait_until=wait_until,
        selector=selector,
        full_page=full_page,
        device_scale_factor=device_scale_factor,
        css_urls=css_urls,
        inline_style=merged_style,
        extra_head_html=extra_head_html,
        base_url=base_url,
        settle_time_ms=settle_time_ms,
    )


def get_render_service() -> RenderService:
    """Return the shared renderer service instance."""
    return _service


def get_render_status() -> RenderServiceStatus:
    """Return a lightweight runtime status for diagnostics."""
    return _service.get_status()


__all__ = [
    "RenderOptions",
    "RenderService",
    "RenderServiceStatus",
    "RenderUnavailableError",
    "get_render_service",
    "get_render_status",
    "html_to_pic",
    "is_playwright_available",
    "markdown_to_pic",
    "playwright_dependency_message",
    "render_html",
    "render_template",
    "render_url",
    "template_to_pic",
    "url_to_pic",
]


get_driver().on_startup(_service.startup)
get_driver().on_shutdown(_service.shutdown)
