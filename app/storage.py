"""Persistent run/attempt history using stdlib SQLite."""

import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from .schemas import RunResult


class RunStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    task TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    answer TEXT NOT NULL,
                    attempts_count INTEGER NOT NULL,
                    total_latency_ms REAL NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    attempt_number INTEGER NOT NULL,
                    tool_name TEXT,
                    tool_input TEXT,
                    tool_output TEXT,
                    answer TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    feedback TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    tokens INTEGER NOT NULL
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_attempts_run ON attempts(run_id)")

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=15)
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 15000")
        return con

    def save(self, result: RunResult) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (result.run_id, datetime.now(timezone.utc).isoformat(), result.task,
                 result.provider, int(result.success), result.answer, len(result.attempts),
                 result.total_latency_ms, result.total_tokens,
                 json.dumps(result.model_dump())),
            )
            con.executemany(
                """INSERT INTO attempts
                   (run_id, attempt_number, tool_name, tool_input, tool_output, answer,
                    passed, feedback, latency_ms, tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(result.run_id, attempt.number,
                  attempt.plan.tool if attempt.plan else None,
                  attempt.plan.tool_input if attempt.plan else None,
                  attempt.tool_output, attempt.answer, int(attempt.passed),
                  attempt.feedback, attempt.latency_ms, attempt.tokens)
                 for attempt in result.attempts],
            )

    def get(self, run_id: str) -> dict | None:
        with self._connect() as con:
            row = con.execute("SELECT payload_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def recent(self, limit: int = 20) -> list[dict]:
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                """SELECT run_id, created_at, task, provider, success, attempts_count,
                          total_latency_ms, total_tokens FROM runs
                   ORDER BY created_at DESC LIMIT ?""", (limit,)
            ).fetchall()
        return [dict(row) | {"success": bool(row["success"])} for row in rows]
