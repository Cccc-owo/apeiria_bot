"""Web UI plugin — management dashboard API + static file serving."""
from pathlib import Path

from nonebot.plugin import PluginMetadata

from apeiria.core.configs.models import PluginExtraData, PluginType, RegisterConfig
from apeiria.core.i18n import load_locales, t

load_locales(Path(__file__).parent / "locales")

__plugin_meta__ = PluginMetadata(
    name="Web管理面板",
    description="Web UI 管理面板 API",
    usage="访问 http://host:port/ 打开管理面板",
    extra=PluginExtraData(
        author="apeiria",
        version="0.1.0",
        plugin_type=PluginType.HIDDEN,
        admin_level=0,
        configs=[
            RegisterConfig(
                key="token_expire_days",
                default=7,
                help="JWT token expiration days for the Web UI",
                type=int,
            )
        ],
        required_plugins=["nonebot_plugin_localstore", "nonebot_plugin_orm"],
    ).to_dict(),
)

_WEB_DIR = Path(__file__).parent.parent.parent.parent / "web"
_DIST_DIR = _WEB_DIR / "dist"


def _web_ui_url() -> str:
    """Build the current Web UI URL from driver config."""
    import nonebot

    config = nonebot.get_driver().config
    host = str(getattr(config, "host", "127.0.0.1"))
    port = int(getattr(config, "port", 8080))
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"http://{host}:{port}/"


def _mount_routes() -> None:
    """Mount API routes + static frontend into nonebot's ASGI app."""
    import logging

    import nonebot
    from nonebot.log import logger

    app = nonebot.get_app()

    from .routes import router

    app.include_router(router, prefix="/api")

    # Redirect uvicorn access logs to file instead of console
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "access.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    access_logger.addHandler(file_handler)

    if _DIST_DIR.is_dir():
        from fastapi.staticfiles import StaticFiles
        from starlette.responses import FileResponse

        @app.get("/{path:path}", include_in_schema=False)
        async def _spa_fallback(path: str) -> FileResponse:
            file = _DIST_DIR / path
            if file.is_file():
                return FileResponse(file)
            return FileResponse(_DIST_DIR / "index.html")

        assets_dir = _DIST_DIR / "assets"
        if assets_dir.is_dir():
            app.mount(
                "/assets",
                StaticFiles(directory=assets_dir),
                name="static",
            )
        logger.info(
            "{}",
            t("web_ui.startup.ready", url=_web_ui_url()),
        )

        from .secrets import get_secret_file_path

        logger.info(
            "{}",
            t("web_ui.startup.credentials_file", path=get_secret_file_path()),
        )
    else:
        logger.warning("{}", t("web_ui.startup.build_disabled"))
        logger.debug("Web UI frontend assets not found in {}", _DIST_DIR)


from nonebot import get_driver

get_driver().on_startup(_mount_routes)
