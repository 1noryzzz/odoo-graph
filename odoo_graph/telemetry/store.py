"""SQLite storage for local CLI telemetry."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping


TELEMETRY_SCHEMA_VERSION = 1
DEFAULT_DB_PATH = Path.home() / ".cache" / "odoo-graph" / "telemetry.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cli_invocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    telemetry_schema_version INTEGER NOT NULL,
    package_version TEXT NOT NULL,
    entrypoint TEXT NOT NULL DEFAULT 'cli',

    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_total_ms INTEGER,
    duration_load_ms INTEGER,
    duration_query_ms INTEGER,
    duration_output_ms INTEGER,

    codex_thread_id TEXT,
    codex_turn_id TEXT,
    session_key TEXT,
    session_gap_seconds INTEGER,

    command TEXT NOT NULL,

    target_raw TEXT,
    target_kind TEXT,
    target_model TEXT,
    target_field TEXT,
    target_method TEXT,
    target_module TEXT,

    start_raw TEXT,
    start_kind TEXT,
    start_model TEXT,
    start_field TEXT,

    max_depth INTEGER,
    max_paths INTEGER,
    allow_kinds TEXT,

    success INTEGER NOT NULL,
    exit_code INTEGER,
    result_status TEXT NOT NULL,
    error_category TEXT,
    empty_result INTEGER NOT NULL DEFAULT 0,
    result_size INTEGER,

    argv_json TEXT,
    target_meta_json TEXT,
    result_summary_json TEXT,
    extra_json TEXT,

    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_thread_time
    ON cli_invocations (codex_thread_id, started_at);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_session_time
    ON cli_invocations (session_key, started_at);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_command
    ON cli_invocations (command);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_target
    ON cli_invocations (target_kind, target_raw);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_result
    ON cli_invocations (success, result_status, error_category);
"""

COLUMNS = (
    "telemetry_schema_version",
    "package_version",
    "entrypoint",
    "started_at",
    "ended_at",
    "duration_total_ms",
    "duration_load_ms",
    "duration_query_ms",
    "duration_output_ms",
    "codex_thread_id",
    "codex_turn_id",
    "session_key",
    "session_gap_seconds",
    "command",
    "target_raw",
    "target_kind",
    "target_model",
    "target_field",
    "target_method",
    "target_module",
    "start_raw",
    "start_kind",
    "start_model",
    "start_field",
    "max_depth",
    "max_paths",
    "allow_kinds",
    "success",
    "exit_code",
    "result_status",
    "error_category",
    "empty_result",
    "result_size",
    "argv_json",
    "target_meta_json",
    "result_summary_json",
    "extra_json",
)


def telemetry_db_path(path: str | os.PathLike | None = None) -> Path:
    if path:
        return Path(path).expanduser()
    env = os.environ.get("ODOO_GRAPH_TELEMETRY_DB")
    if env:
        return Path(env).expanduser()
    return DEFAULT_DB_PATH


def connect(path: str | os.PathLike | None = None) -> sqlite3.Connection:
    db_path = telemetry_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 3000")
    return con


def init_db(path: str | os.PathLike | None = None) -> Path:
    db_path = telemetry_db_path(path)
    with connect(db_path) as con:
        con.executescript(SCHEMA)
    return db_path


def dumps_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def insert_invocation(
    row: Mapping[str, Any],
    path: str | os.PathLike | None = None,
) -> None:
    init_db(path)
    values = {key: row.get(key) for key in COLUMNS}
    for key in ("argv_json", "target_meta_json", "result_summary_json", "extra_json"):
        if values[key] is not None and not isinstance(values[key], str):
            values[key] = dumps_json(values[key])
    placeholders = ", ".join("?" for _ in COLUMNS)
    columns = ", ".join(COLUMNS)
    sql = f"INSERT INTO cli_invocations ({columns}) VALUES ({placeholders})"
    with connect(path) as con:
        con.execute(sql, [values[key] for key in COLUMNS])


def fetch_invocations(path: str | os.PathLike | None = None) -> list[dict]:
    db_path = telemetry_db_path(path)
    if not db_path.exists():
        return []
    with connect(db_path) as con:
        rows: Iterable[sqlite3.Row] = con.execute(
            "SELECT * FROM cli_invocations ORDER BY started_at, id"
        )
        return [dict(row) for row in rows]
