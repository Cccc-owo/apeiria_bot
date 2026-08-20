from __future__ import annotations

import json
from types import SimpleNamespace

from apeiria.web.logs import LogHub, _iter_reverse_lines


def _write_log(path, rows: list[dict]) -> None:
    lines = [json.dumps({"record": row}, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_iter_reverse_lines_with_trailing_newline(tmp_path) -> None:
    path = tmp_path / "a.log"
    path.write_text("1\n2\n3\n", encoding="utf-8")

    assert list(_iter_reverse_lines(path)) == ["3", "2", "1"]


def test_iter_reverse_lines_without_trailing_newline(tmp_path) -> None:
    path = tmp_path / "a.log"
    path.write_text("1\n2\n3", encoding="utf-8")

    assert list(_iter_reverse_lines(path)) == ["3", "2", "1"]


def test_read_history_returns_newest_first_and_paginates(tmp_path) -> None:
    path = tmp_path / "app.log"
    _write_log(
        path,
        [
            {
                "time": {"timestamp": 1.0},
                "level": {"no": 20, "name": "INFO"},
                "name": "app",
                "message": "one",
            },
            {
                "time": {"timestamp": 2.0},
                "level": {"no": 20, "name": "INFO"},
                "name": "app",
                "message": "two",
            },
            {
                "time": {"timestamp": 3.0},
                "level": {"no": 30, "name": "WARNING"},
                "name": "app",
                "message": "three",
            },
        ],
    )

    hub = LogHub()
    hub._cfg = SimpleNamespace(file=str(path))

    first = hub.read_history(page=1, size=2)
    assert first["total"] == 3
    assert [item["message"] for item in first["items"]] == ["three", "two"]

    second = hub.read_history(page=2, size=2)
    assert [item["message"] for item in second["items"]] == ["one"]

    warned = hub.read_history(level="WARNING")
    assert warned["total"] == 1
    assert warned["items"][0]["message"] == "three"
