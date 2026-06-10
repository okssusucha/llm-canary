"""SQLite store for the self-hosted server: run history and baselines.

Zero-config by design — a single file database, created on first use, so
`llm-canary serve` works with no external services.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    passed INTEGER NOT NULL,
    summary TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS baselines (
    name TEXT PRIMARY KEY,
    updated_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path):
        path = Path(path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def add_run(
        self, kind: str, name: str, passed: bool, summary: str, payload: dict[str, Any]
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO runs (created_at, kind, name, passed, summary, payload)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (_now(), kind, name, int(passed), summary, json.dumps(payload)),
        )
        self._conn.commit()
        return int(cur.lastrowid or 0)

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, created_at, kind, name, passed, summary FROM runs"
            " ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) | {"passed": bool(row["passed"])} for row in rows]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["passed"] = bool(result["passed"])
        result["payload"] = json.loads(result["payload"])
        return result

    def set_baseline(self, name: str, payload: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO baselines (name, updated_at, payload) VALUES (?, ?, ?)"
            " ON CONFLICT(name) DO UPDATE SET updated_at = excluded.updated_at,"
            " payload = excluded.payload",
            (name, _now(), json.dumps(payload)),
        )
        self._conn.commit()

    def get_baseline(self, name: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT payload FROM baselines WHERE name = ?", (name,)
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def close(self) -> None:
        self._conn.close()
