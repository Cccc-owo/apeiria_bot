"""Web UI plugin — management dashboard API + static file serving."""

import os
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


def _latest_file_mtime(root: Path) -> float | None:
    mtimes = [file.stat().st_mtime for file in root.rglob("*") if file.is_file()]
    return max(mtimes) if mtimes else None


def _has_fresh_dist() -> bool:
    if not _DIST_DIR.is_dir():
        return False
    src_dir = _WEB_DIR / "src"
    if not src_dir.is_dir():
        return False

    dist_mtime = _latest_file_mtime(_DIST_DIR)
    src_mtime = _latest_file_mtime(src_dir)
    return (
        dist_mtime is not None
        and src_mtime is not None
        and src_mtime <= dist_mtime
    )


def _should_build_frontend_on_start() -> bool:
    value = os.getenv("APEIRIA_BUILD_FRONTEND_ON_START")
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _install_frontend_dependencies(pm: str) -> tuple[bool, str]:
    try:
        subprocess.run(
            [pm, "install"],
            cwd=_WEB_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = (
            exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        )
        return False, stderr
    return True, ""


def _run_frontend_build(pm: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [pm, "run", "build"],
            cwd=_WEB_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, str(exc)
    return result.returncode == 0, result.stderr


def _build_frontend() -> bool:
    """Auto build frontend if needed. Quiet unless something goes wrong."""
    from nonebot.log import logger

    available = _DIST_DIR.is_dir()
    should_build = (_WEB_DIR / "package.json").is_file() and not _has_fresh_dist()
    if not should_build:
        return available or (_WEB_DIR / "package.json").is_file()

    if not _should_build_frontend_on_start():
        logger.info("{}", t("web_ui.startup.build_disabled"))
        return available

    pm = shutil.which("pnpm") or shutil.which("npm")
    if not pm:
        logger.warning("{}", t("web_ui.startup.no_package_manager"))
        return available

    if not (_WEB_DIR / "node_modules").is_dir():
        logger.debug("Installing frontend dependencies...")
        installed, stderr = _install_frontend_dependencies(pm)
        if not installed:
            logger.error("{}", t("web_ui.startup.build_failed", stderr=stderr))
            return False

    logger.debug("Building frontend...")
    built, stderr = _run_frontend_build(pm)
    if not built:
        logger.error("{}", t("web_ui.startup.build_failed", stderr=stderr))
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

        from .secrets import get_secret_file_path

        logger.info(
            "{}",
            t("web_ui.startup.credentials_file", path=get_secret_file_path()),
        )
    else:
        logger.debug("Web UI frontend not available")


from nonebot import get_driver

get_driver().on_startup(_mount_routes)
