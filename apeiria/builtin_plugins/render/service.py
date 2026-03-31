"""Unified Playwright-based renderer service."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from html import escape
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape
from nonebot.log import logger

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Playwright

    from .config import RenderConfig

WaitUntilState = Literal["commit", "domcontentloaded", "load", "networkidle"]
ScreenshotType = Literal["png", "jpeg"]


class RenderUnavailableError(RuntimeError):
    """Raised when the render backend is unavailable."""


@dataclass(slots=True)
class RenderOptions:
    """One-off render options for HTML, template, or URL rendering."""

    width: int | None = None
    height: int | None = None
    device_scale_factor: float | None = None
    timeout_ms: int | None = None
    wait_until: WaitUntilState = "networkidle"
    selector: str | None = None
    full_page: bool = False
    image_format: ScreenshotType = "png"
    css_urls: list[str] = field(default_factory=list)
    inline_style: str = ""
    extra_head_html: str = ""
    base_url: str = ""
    settle_time_ms: int = 0


@dataclass(slots=True)
class RenderServiceStatus:
    """Observable runtime status for the shared renderer."""

    playwright_available: bool
    browser_started: bool
    startup_warmup: bool
    warmup_in_progress: bool
    max_concurrency: int
    browser_locale: str


def playwright_dependency_message() -> str:
    return (
        "Playwright renderer is unavailable. Install the `playwright` dependency "
        "and run `playwright install chromium`."
    )


def is_playwright_available() -> bool:
    try:
        return find_spec("playwright.async_api") is not None
    except ModuleNotFoundError:
        return False


class RenderService:
    """Shared browser renderer with eager startup warmup and bounded concurrency."""

    def __init__(self, config: RenderConfig) -> None:
        self._config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._warmup_task: asyncio.Task[None] | None = None
        self._startup_lock = asyncio.Lock()
        self._template_environments: dict[Path, Environment] = {}
        self._semaphore = asyncio.Semaphore(config.max_concurrency)

    async def startup(self) -> None:
        """Start browser warmup in the background during startup."""
        if not self._config.startup_warmup:
            return
        if self._warmup_task is not None and not self._warmup_task.done():
            return
        self._warmup_task = asyncio.create_task(
            self._warmup_browser(),
            name="apeiria-render-warmup",
        )

    async def shutdown(self) -> None:
        """Close the shared browser process and Playwright runtime."""
        warmup_task = self._warmup_task
        self._warmup_task = None
        if warmup_task is not None and not warmup_task.done():
            warmup_task.cancel()
            with suppress(asyncio.CancelledError):
                await warmup_task
        async with self._startup_lock:
            await self._close_runtime()

    def get_status(self) -> RenderServiceStatus:
        """Return a lightweight runtime status snapshot."""
        return RenderServiceStatus(
            playwright_available=is_playwright_available(),
            browser_started=self._browser is not None,
            startup_warmup=self._config.startup_warmup,
            warmup_in_progress=self._warmup_task is not None
            and not self._warmup_task.done(),
            max_concurrency=self._config.max_concurrency,
            browser_locale=self._config.browser_locale,
        )

    async def render_html(
        self,
        html: str,
        *,
        options: RenderOptions | None = None,
    ) -> bytes:
        """Render raw HTML or an HTML fragment to an image."""
        opts = options or RenderOptions()
        document = _build_html_document(
            html,
            css_urls=opts.css_urls,
            inline_style=opts.inline_style,
            extra_head_html=opts.extra_head_html,
            base_url=opts.base_url,
        )
        async with self._semaphore:
            context = await self._new_context(opts)
            try:
                page = await context.new_page()
                timeout_ms = _timeout_ms(self._config, opts)
                page.set_default_timeout(timeout_ms)
                await page.set_content(document, wait_until="domcontentloaded")
                await self._wait_for_ready_state(page, opts, timeout_ms)
                await self._maybe_wait_for_settle(opts)
                return await self._take_screenshot(page, opts, timeout_ms)
            finally:
                await context.close()

    async def render_url(
        self,
        url: str,
        *,
        options: RenderOptions | None = None,
    ) -> bytes:
        """Render a remote or local URL to an image."""
        opts = options or RenderOptions()
        async with self._semaphore:
            context = await self._new_context(opts)
            try:
                page = await context.new_page()
                timeout_ms = _timeout_ms(self._config, opts)
                page.set_default_timeout(timeout_ms)
                await page.goto(url, wait_until=opts.wait_until, timeout=timeout_ms)
                await self._maybe_wait_for_settle(opts)
                return await self._take_screenshot(page, opts, timeout_ms)
            finally:
                await context.close()

    async def render_template(
        self,
        template_name: str,
        *,
        context: dict[str, Any] | None = None,
        template_dir: str | Path,
        options: RenderOptions | None = None,
    ) -> bytes:
        """Render one Jinja template file to an image."""
        environment = self._get_template_environment(template_dir)
        template = environment.get_template(template_name)
        html = template.render(**(context or {}))
        return await self.render_html(html, options=options)

    def _get_template_environment(self, template_dir: str | Path) -> Environment:
        template_root = Path(template_dir).resolve()
        environment = self._template_environments.get(template_root)
        if environment is not None:
            return environment

        environment = Environment(
            loader=FileSystemLoader(str(template_root)),
            autoescape=select_autoescape(
                disabled_extensions=("txt",),
                default=True,
                default_for_string=True,
            ),
        )
        self._template_environments[template_root] = environment
        return environment

    async def _warmup_browser(self) -> None:
        try:
            await self._ensure_browser()
        except RenderUnavailableError as exc:
            logger.warning(f"Render warmup skipped: {exc}")
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Render warmup failed unexpectedly")

    async def _ensure_browser(self) -> Browser:
        browser = self._browser
        if browser is not None and browser.is_connected():
            return browser

        async with self._startup_lock:
            browser = self._browser
            if browser is not None and browser.is_connected():
                return browser

            await self._close_runtime()

            if not is_playwright_available():
                raise RenderUnavailableError(playwright_dependency_message())

            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            launch_kwargs: dict[str, Any] = {
                "headless": self._config.headless,
                "args": list(self._config.launch_args),
            }
            if self._config.channel:
                launch_kwargs["channel"] = self._config.channel
            if self._config.executable_path:
                launch_kwargs["executable_path"] = self._config.executable_path

            try:
                browser = await playwright.chromium.launch(**launch_kwargs)
            except Exception as exc:
                await playwright.stop()
                message = (
                    "Failed to launch Playwright Chromium. "
                    "Run `playwright install chromium` and verify browser "
                    "dependencies are installed."
                )
                raise RenderUnavailableError(message) from exc

            browser.on("disconnected", self._handle_browser_disconnected)
            self._playwright = playwright
            self._browser = browser
            return browser

    async def _new_context(self, options: RenderOptions) -> BrowserContext:
        browser = await self._ensure_browser()
        viewport = {
            "width": max(options.width or self._config.default_width, 1),
            "height": max(options.height or self._config.default_height, 1),
        }
        kwargs: dict[str, Any] = {
            "viewport": viewport,
            "device_scale_factor": max(
                options.device_scale_factor or self._config.default_device_scale_factor,
                1.0,
            ),
            "locale": self._config.browser_locale,
        }
        if self._config.user_agent:
            kwargs["user_agent"] = self._config.user_agent
        return await browser.new_context(**kwargs)

    async def _wait_for_ready_state(
        self,
        page: Any,
        options: RenderOptions,
        timeout_ms: int,
    ) -> None:
        if options.wait_until in {"commit", "domcontentloaded"}:
            return
        await page.wait_for_load_state(options.wait_until, timeout=timeout_ms)

    async def _maybe_wait_for_settle(self, options: RenderOptions) -> None:
        settle_time_ms = max(options.settle_time_ms, 0)
        if settle_time_ms > 0:
            await asyncio.sleep(settle_time_ms / 1000)

    async def _take_screenshot(
        self,
        page: Any,
        options: RenderOptions,
        timeout_ms: int,
    ) -> bytes:
        if options.selector:
            locator = page.locator(options.selector)
            await locator.wait_for(state="visible", timeout=timeout_ms)
            return await locator.screenshot(type=options.image_format)
        return await page.screenshot(
            type=options.image_format,
            full_page=options.full_page,
        )

    async def _close_runtime(self) -> None:
        browser = self._browser
        self._browser = None
        if browser is not None:
            try:
                await browser.close()
            except Exception:  # noqa: BLE001
                logger.debug("Render browser close raised during shutdown")

        playwright = self._playwright
        self._playwright = None
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception:  # noqa: BLE001
                logger.debug("Playwright runtime close raised during shutdown")

    def _handle_browser_disconnected(self, *_: object) -> None:
        self._browser = None
        self._playwright = None
        logger.warning("Render browser disconnected, next request will relaunch it.")


def _timeout_ms(config: RenderConfig, options: RenderOptions) -> int:
    return max(options.timeout_ms or config.default_timeout_ms, 1)


def _build_html_document(
    html: str,
    *,
    css_urls: list[str],
    inline_style: str,
    extra_head_html: str,
    base_url: str,
) -> str:
    parts = []
    if base_url.strip():
        parts.append(f'<base href="{escape(base_url.strip(), quote=True)}">')
    parts.extend(_css_link(url) for url in css_urls if url)
    parts.append(extra_head_html)
    parts.append(_style(inline_style))
    head_markup = "\n".join(item for item in parts if item).strip()
    lower_html = html.lower()

    if "<html" in lower_html:
        if "</head>" in lower_html:
            head_index = lower_html.find("</head>")
            return html[:head_index] + head_markup + "\n" + html[head_index:]

        html_tag_start = lower_html.find("<html")
        html_tag_end = lower_html.find(">", html_tag_start)
        if html_tag_end != -1:
            insertion_point = html_tag_end + 1
            return (
                html[:insertion_point]
                + f"<head>{head_markup}</head>"
                + html[insertion_point:]
            )

    template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {{ head_markup | safe }}
</head>
<body>
  {{ html | safe }}
</body>
</html>
""".strip()
    return (
        Environment(autoescape=False)
        .from_string(template)
        .render(
            head_markup=head_markup,
            html=html,
        )
    )


def _css_link(url: str) -> str:
    return f'<link rel="stylesheet" href="{escape(url, quote=True)}">'


def _style(content: str) -> str:
    if not content.strip():
        return ""
    return f"<style>{content}</style>"
