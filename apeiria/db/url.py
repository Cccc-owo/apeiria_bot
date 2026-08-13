from __future__ import annotations


def build_db_url(path: str) -> str:
    return f"sqlite+aiosqlite:///{path}"


__all__ = ["build_db_url"]
