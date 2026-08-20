from __future__ import annotations

from apeiria.jobs.uv import find_uv, sync_apeiria_env_sync

# Backwards-compatible alias used by existing tests and callers.
_find_uv = find_uv


def sync_apeiria_env() -> bool:
    return sync_apeiria_env_sync()
