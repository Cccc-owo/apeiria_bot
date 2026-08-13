from __future__ import annotations

from apeiria.db.url import build_db_url


def test_build_db_url() -> None:
    assert build_db_url("data/x.db") == "sqlite+aiosqlite:///data/x.db"
