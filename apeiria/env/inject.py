"""Inject the ``.apeiria`` plugin venv site-packages into the interpreter path."""

from __future__ import annotations

import site
from pathlib import Path

from nonebot.log import logger

_injected: set[str] = set()


def _resolve_site_packages(venv_path: Path) -> Path | None:
    """Return the first site-packages directory found in the given venv.

    Args:
        venv_path (Path): Path to the virtual environment to inspect.

    Returns:
        The first ``lib/python*/site-packages`` directory found, or ``None``
        if no such directory exists.
    """
    for lib_dir in sorted(venv_path.glob("lib/python*/site-packages")):
        return lib_dir
    return None


def inject_apeiria_paths() -> None:
    """Inject the ``.apeiria`` plugin venv into the interpreter site-packages.

    Resolves the site-packages directory of ``.apeiria/.venv`` and adds it
    via :func:`site.addsitedir`. Once injected, the path is recorded so later
    calls become no-ops. A missing venv or site-packages directory is logged
    as a warning rather than raising.
    """
    venv_path = Path(".apeiria/.venv")
    if not venv_path.exists():
        logger.warning("Plugin venv not found at {}. Run sync first.", venv_path)
        return

    sp = _resolve_site_packages(venv_path)
    if sp is None:
        logger.warning("Plugin site-packages not found")
        return

    site_packages_str = str(sp.resolve())
    if site_packages_str in _injected:
        return

    site.addsitedir(site_packages_str)
    _injected.add(site_packages_str)
    logger.info("Injected plugin path: {}", site_packages_str)
