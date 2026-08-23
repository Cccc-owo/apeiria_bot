"""Sync the ``.apeiria`` plugin environment with ``uv sync``."""

from __future__ import annotations

from apeiria.jobs.uv import find_uv, sync_apeiria_env_sync

# Backwards-compatible alias used by existing tests and callers.
_find_uv = find_uv


def sync_apeiria_env() -> bool:
    """Run ``uv sync`` to install the ``.apeiria`` plugin environment.

    Returns:
        ``True`` if the sync succeeded, ``False`` otherwise.
    """
    return sync_apeiria_env_sync()
