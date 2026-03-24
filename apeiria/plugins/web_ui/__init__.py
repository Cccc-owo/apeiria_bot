"""Web UI plugin — management dashboard API + static file serving."""

import shutil
import subprocess
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


def _build_frontend() -> bool:
    """Auto build frontend if needed. Quiet unless something goes wrong."""
    from nonebot.log import logger

    if not (_WEB_DIR / "package.json").is_file():
        return _DIST_DIR.is_dir()

    if _DIST_DIR.is_dir():
        src_dir = _WEB_DIR / "src"
        if src_dir.is_dir():
            dist_mtime = max(
                f.stat().st_mtime for f in _DIST_DIR.rglob("*") if f.is_file()
            )
            src_mtime = max(
                f.stat().st_mtime for f in src_dir.rglob("*") if f.is_file()
            )
            if src_mtime <= dist_mtime:
                return True

    pm = shutil.which("pnpm") or shutil.which("npm")
    if not pm:
        logger.warning("{}", t("web_ui.startup.no_package_manager"))
        return _DIST_DIR.is_dir()

    if not (_WEB_DIR / "node_modules").is_dir():
        logger.debug("Installing frontend dependencies...")
        subprocess.run([pm, "install"], cwd=_WEB_DIR, check=True, capture_output=True)

    logger.debug("Building frontend...")
    result = subprocess.run(
        [pm, "run", "build"],
        cwd=_WEB_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("{}", t("web_ui.startup.build_failed", stderr=result.stderr))
        return False

    logger.info("{}", t("web_ui.startup.build_success"))
    return True


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

    # Auto build + serve frontend
    _build_frontend()

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
            t("web_ui.startup.ready", url="http://127.0.0.1:8080/"),
        )

        from .secrets import get_password

        logger.info("{}", t("web_ui.startup.password", password=get_password()))
    else:
        logger.debug("Web UI frontend not available")


from nonebot import get_driver

get_driver().on_startup(_mount_routes)
