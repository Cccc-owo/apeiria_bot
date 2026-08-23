"""Utilities for constructing Apeiria database connection URLs."""

from __future__ import annotations


def build_db_url(path: str) -> str:
    """Build a SQLite database URL from the given file path.

    Args:
        path: Filesystem path to the SQLite database file.

    Returns:
        The constructed ``sqlite+aiosqlite`` database URL.
    """
    return f"sqlite+aiosqlite:///{path}"


__all__ = ["build_db_url"]
