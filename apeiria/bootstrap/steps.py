"""Concrete bootstrap steps executed during project startup."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import nonebot
from nonebot.log import logger
from nonebot.message import event_postprocessor

from apeiria.access.control import AccessControl
from apeiria.env.ensure import ensure_apeiria_env
from apeiria.env.inject import inject_apeiria_paths
from apeiria.env.sync import sync_apeiria_env
from apeiria.plugin.scanner import (
    local_plugin_module_name,
    manifest_module_candidate,
    scan_plugins,
)

_access_control: AccessControl | None = None
_conversation_hook_installed = False
_require_tracker_installed = False


def get_access_control() -> AccessControl:
    """Return the initialized access-control instance.

    Returns:
        The shared :class:`AccessControl` instance.

    Raises:
        RuntimeError: If access control has not been initialized yet.
    """
    if _access_control is None:
        raise RuntimeError("Access control not initialized")  # noqa: TRY003
    return _access_control


def step_db_migrate() -> None:
    """Apply all Alembic database migrations up to the head revision."""
    from alembic.config import Config

    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.success("Database migrations applied")


def step_db_shutdown() -> None:
    """Install a driver shutdown hook that closes the database engine."""
    from apeiria.db.engine import close_db

    @nonebot.get_driver().on_shutdown
    async def _close_db() -> None:
        """Close the database engine cleanly on shutdown."""
        await close_db()

    logger.success("DB graceful-shutdown hook installed")


def step_apeiria_ensure() -> None:
    """Ensure the plugin environment is created and ready for use."""
    ensure_apeiria_env()
    logger.success("Plugin environment ensured")


def step_apeiria_sync() -> None:
    """Sync the plugin environment against the managed dependency lockfile."""
    if sync_apeiria_env():
        logger.success("Plugin environment synced")


def step_apeiria_inject() -> None:
    """Inject the plugin environment paths into the interpreter."""
    inject_apeiria_paths()


def _read_adapter_states() -> dict[str, dict]:
    """Return the enabled states of adapters from the adapters YAML file.

    Returns:
        A mapping of adapter name to its state, or an empty dict when the file
        does not exist or contains no states.
    """
    import yaml

    yaml_path = Path(".apeiria/adapters.yaml")
    if not yaml_path.exists():
        return {}
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    return data.get("states") or {}


def step_require_tracker() -> None:
    """Install a wrapper around ``require`` that records plugin dependencies."""
    global _require_tracker_installed  # noqa: PLW0603
    if _require_tracker_installed:
        return

    import inspect

    from nonebot.plugin import get_plugin, get_plugin_by_module_name
    from nonebot.plugin import load as plugin_load
    from nonebot.plugin.load import require as original_require

    from apeiria.plugin.dependency_graph import record_dependency

    def _tracking_require(name: str) -> ModuleType:
        """Require a plugin and record the dependency from the calling plugin.

        Args:
            name: Name of the plugin to require.

        Returns:
            The module returned by the original ``require`` call.
        """
        module = original_require(name)
        frame = inspect.currentframe()
        try:
            caller = frame.f_back if frame is not None else None
            if caller is None:
                return module
            caller_module = caller.f_globals.get("__name__")
            if not caller_module:
                return module
            current = get_plugin_by_module_name(caller_module)
            if current is None:
                return module
            dep = get_plugin(name) or get_plugin_by_module_name(name)
            if dep is not None:
                record_dependency(current.name, dep.name)
        finally:
            del frame
        return module

    nonebot.require = _tracking_require  # ty: ignore[invalid-assignment]
    nonebot.plugin.require = _tracking_require  # ty: ignore[invalid-assignment]
    plugin_load.require = _tracking_require  # ty: ignore[invalid-assignment]
    _require_tracker_installed = True
    logger.success("Require dependency tracker installed")


def step_load_builtin_adapters() -> None:
    """Load the builtin adapters declared in the project pyproject.toml."""
    from apeiria.config.loader import load_adapters_from_toml

    states = _read_adapter_states()
    load_adapters_from_toml("pyproject.toml", states=states)


def step_load_adapters() -> None:
    """Load the adapters defined in the plugin-environment pyproject.toml."""
    from apeiria.config.loader import load_adapters_from_toml

    states = _read_adapter_states()
    load_adapters_from_toml(".apeiria/pyproject.toml", states=states)


def step_load_builtins() -> None:
    """Load all enabled builtin plugins."""
    loaded = 0
    for manifest in scan_plugins():
        if manifest.source != "builtin":
            continue
        if not manifest.enabled:
            logger.debug("Skipped disabled builtin plugin: {}", manifest.name)
            continue
        nonebot.load_plugin(manifest.path_or_module)
        loaded += 1
        logger.debug("Loaded builtin plugin: {}", manifest.name)

    if loaded:
        logger.success("Loaded {} builtin plugin(s)", loaded)


def step_load_local() -> None:
    """Load all enabled local plugins from the plugin environment."""
    import sys

    loaded = 0
    for manifest in scan_plugins():
        if manifest.source != "local":
            continue
        if not manifest.enabled:
            logger.debug("Skipped disabled local plugin: {}", manifest.name)
            continue

        plugin_dir = Path(manifest.path_or_module)
        if not plugin_dir.is_dir():
            logger.warning("Skipped local plugin missing directory: {}", plugin_dir)
            continue

        module = local_plugin_module_name(plugin_dir)
        if module is None:
            logger.warning(
                "Skipped local plugin with invalid module name: {}", plugin_dir
            )
            continue

        package_root = plugin_dir.parent.parent
        package_root_key = str(package_root.resolve())
        if package_root_key not in sys.path:
            sys.path.insert(0, package_root_key)

        try:
            nonebot.load_plugin(module)
        except Exception:  # noqa: BLE001
            logger.opt(exception=True).warning(
                "Failed to load local plugin: {}", module
            )
            continue
        loaded += 1
        logger.debug("Loaded local plugin: {}", module)

    if loaded:
        logger.success("Loaded {} local plugin(s)", loaded)


def step_load_pypi() -> None:
    """Load all enabled plugins installed from PyPI."""
    loaded = 0
    for manifest in scan_plugins():
        if manifest.source != "pypi":
            continue
        if not manifest.enabled:
            logger.debug("Skipped disabled PyPI plugin: {}", manifest.name)
            continue
        module = manifest_module_candidate(manifest)
        if not module:
            continue
        try:
            nonebot.load_plugin(module)
        except Exception:  # noqa: BLE001
            logger.opt(exception=True).warning(
                "Failed to load PyPI plugin: {} ({})", manifest.name, module
            )
            continue
        loaded += 1
        logger.debug("Loaded PyPI plugin: {} ({})", manifest.name, module)

    if loaded:
        logger.success("Loaded {} PyPI plugin(s)", loaded)


def step_conversation() -> None:
    """Install the message-persistence hook on the event postprocessor."""
    global _conversation_hook_installed  # noqa: PLW0603
    if _conversation_hook_installed:
        return

    from apeiria.conversation.hook import persist

    event_postprocessor(persist)
    _conversation_hook_installed = True
    logger.success("Message persistence hook installed")


def step_access() -> None:
    """Initialize access control and install its access hooks."""
    global _access_control  # noqa: PLW0603
    _access_control = AccessControl()

    from apeiria.access.hook import install_access_hook

    install_access_hook()

    @nonebot.get_driver().on_startup
    async def _load_rules() -> None:
        """Load the access rules snapshot on driver startup."""
        assert _access_control is not None
        await _access_control.load_snapshot()

    @nonebot.get_driver().on_bot_connect
    async def _reload_rules(bot: nonebot.adapters.Bot) -> None:  # noqa: ARG001  # pyright: ignore[reportAttributeAccessIssue]
        """Reload the access rules snapshot when a bot connects.

        Args:
            bot: The bot that connected to the driver.
        """
        assert _access_control is not None
        await _access_control.load_snapshot()

    logger.success("Access control initialized")


def step_webchat() -> None:
    """Register the WebChat adapter and its helpers when WebChat is enabled."""
    from apeiria.webchat.config import get_webchat_config

    if not get_webchat_config().enabled:
        logger.info("WebChat disabled — skipping registration")
        return

    from apeiria.webchat.adapter import WebChatAdapter
    from apeiria.webchat.alconna import register_alconna
    from apeiria.webchat.uninfo import register_uninfo

    nonebot.get_driver().register_adapter(WebChatAdapter)
    register_uninfo()
    register_alconna()
    logger.success("WebChat adapter registered")


def _source_fingerprint(src_dir: Path) -> str:
    """Return a SHA-256 fingerprint of the frontend source files.

    Args:
        src_dir: Directory containing the frontend source files.

    Returns:
        A hexadecimal SHA-256 digest over the source files in the directory.
    """
    import hashlib

    hasher = hashlib.sha256()
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix not in (".vue", ".ts", ".js", ".css", ".json", ".html"):
            continue
        hasher.update(str(f.relative_to(src_dir)).encode())
        hasher.update(f.read_bytes())
    return hasher.hexdigest()


def _needs_frontend_build(dist_dir: Path) -> bool:
    """Return whether the frontend distribution needs a fresh build.

    Args:
        dist_dir: Directory containing the built frontend assets.

    Returns:
        True if a rebuild is required, False otherwise.
    """
    index = dist_dir / "index.html"
    if not index.is_file():
        return True

    src_dir = Path("webui/src")
    if not src_dir.is_dir():
        return False

    current = _source_fingerprint(src_dir)
    fingerprint_file = dist_dir / ".build_fingerprint"
    try:
        stored = fingerprint_file.read_text().strip()
    except (OSError, ValueError):
        return True
    return stored != current


def _resolve_frontend_file(frontend_dir: Path, full_path: str) -> Path | None:
    """Resolve a request path to a file inside the frontend root.

    Args:
        frontend_dir: Root directory of the built frontend assets.
        full_path: Requested path relative to the frontend root.

    Returns:
        The resolved file path, falling back to index.html when the requested
        path does not exist, or None when the path escapes the frontend root.
    """
    frontend_root = frontend_dir.resolve()
    candidate = (frontend_dir / full_path).resolve()
    if not candidate.is_relative_to(frontend_root):
        return None
    if not candidate.is_file():
        candidate = (frontend_dir / "index.html").resolve()
    return candidate


def _try_auto_build_frontend() -> None:
    """Build the frontend with pnpm when a rebuild is needed and tooling is present."""
    import shutil
    import subprocess

    if not shutil.which("pnpm") or not shutil.which("node"):
        logger.debug("pnpm/node not available, skipping frontend auto-build")
        return

    frontend_dir = Path("webui")
    dist_dir = frontend_dir / "dist"

    if not _needs_frontend_build(dist_dir):
        return

    logger.info("Frontend build needed — running pnpm build in webui/ ...")
    try:
        subprocess.run(
            ["pnpm", "install", "--frozen-lockfile"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        result = subprocess.run(
            ["pnpm", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("Frontend build failed:\n{}", result.stderr[-500:])
        else:
            logger.success("Frontend build completed")
    except OSError as e:
        logger.warning("Failed to run frontend build: {}", e)


def step_web() -> None:
    """Configure the FastAPI web app and register its routes and middleware."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse

    from apeiria.config.loader import load_config
    from apeiria.web.auth import auth_router, ensure_credentials
    from apeiria.web.logs import (
        logs_router,
        quiet_asgi_cancel_errors,
        route_access_logs,
    )
    from apeiria.web.routes import access_router, router
    from apeiria.web.update import router as update_router

    driver = nonebot.get_driver()
    raw_app = getattr(driver, "server_app", None) or getattr(driver, "asgi", None)
    if raw_app is None:
        logger.warning("Web app not available — driver does not support ASGI")
        return
    app: FastAPI = raw_app

    app_config = load_config("data/config.yaml")
    ensure_credentials()
    route_access_logs(app_config.apeiria.logging)
    quiet_asgi_cancel_errors()

    app.include_router(auth_router)
    app.include_router(access_router)
    app.include_router(logs_router)
    app.include_router(router)
    app.include_router(update_router)

    frontend_dir = Path("webui/dist")

    _try_auto_build_frontend()

    @app.get("/{full_path:path}")
    async def _serve_frontend(full_path: str) -> FileResponse:
        """Serve a built frontend asset for a request path.

        Args:
            full_path: Request path relative to the frontend root.

        Returns:
            A :class:`FileResponse` for the resolved asset.

        Raises:
            HTTPException: If the frontend is not built, the requested path is
                not found, or the resolved asset does not exist.
        """
        if not frontend_dir.exists():
            raise HTTPException(status_code=404, detail="Frontend not built")
        candidate = _resolve_frontend_file(frontend_dir, full_path)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Not found")
        if not candidate.exists():
            raise HTTPException(status_code=404, detail="Frontend not built")
        return FileResponse(str(candidate))

    logger.success("Web UI routes registered")
