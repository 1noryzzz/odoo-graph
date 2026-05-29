import json
import sqlite3

from odoo_graph.cli import main
from odoo_graph.resolve import resolve_paths
from odoo_graph.telemetry.report import build_report
from odoo_graph.telemetry.store import fetch_invocations, init_db, insert_invocation
from odoo_graph.tests.fixtures import build_fixture


def _bootstrap(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    return str(tmp_path)


def _row(**overrides):
    row = {
        "telemetry_schema_version": 1,
        "package_version": "test",
        "entrypoint": "cli",
        "started_at": "2026-05-29T00:00:00.000Z",
        "ended_at": "2026-05-29T00:00:00.100Z",
        "duration_total_ms": 100,
        "duration_load_ms": None,
        "duration_query_ms": 1,
        "duration_output_ms": 1,
        "codex_thread_id": "thread-1",
        "codex_turn_id": None,
        "session_key": None,
        "session_gap_seconds": 60,
        "command": "field",
        "target_raw": "res.partner.name",
        "target_kind": "field",
        "target_model": "res.partner",
        "target_field": "name",
        "target_method": None,
        "target_module": None,
        "start_raw": None,
        "start_kind": None,
        "start_model": None,
        "start_field": None,
        "max_depth": None,
        "max_paths": None,
        "allow_kinds": None,
        "success": 1,
        "exit_code": 0,
        "result_status": "success_non_empty",
        "error_category": "none",
        "empty_result": 0,
        "result_size": 1,
        "argv_json": {"argv": ["field", "res.partner.name"]},
        "target_meta_json": None,
        "result_summary_json": None,
        "extra_json": None,
    }
    row.update(overrides)
    return row


def test_telemetry_init_creates_schema(tmp_path):
    db = tmp_path / "telemetry.sqlite3"
    assert init_db(db) == db
    with sqlite3.connect(db) as con:
        names = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"
            )
        }
    assert "cli_invocations" in names
    assert "idx_cli_invocations_command" in names


def test_telemetry_cli_init_and_report(tmp_path, capsys):
    db = tmp_path / "telemetry.sqlite3"

    rc = main(["telemetry", "init", "--db", str(db)])

    assert rc == 0
    assert str(db) in capsys.readouterr().out
    insert_invocation(_row(), db)

    rc = main(["telemetry", "report", "--db", str(db), "-f", "json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["analysis"]["invocation_count"] == 1


def test_cli_writes_business_invocation_telemetry(tmp_path, monkeypatch, capsys):
    db = tmp_path / "telemetry.sqlite3"
    out = _bootstrap(tmp_path / "dump")
    monkeypatch.setenv("ODOO_GRAPH_TELEMETRY", "1")
    monkeypatch.setenv("ODOO_GRAPH_TELEMETRY_DB", str(db))

    rc = main(["field", "res.partner.display_name", "--out-dir", out, "-f", "json"])

    assert rc == 0
    json.loads(capsys.readouterr().out)
    rows = fetch_invocations(db)
    assert len(rows) == 1
    row = rows[0]
    assert row["command"] == "field"
    assert row["target_model"] == "res.partner"
    assert row["target_field"] == "display_name"
    assert row["success"] == 1
    assert row["result_status"] == "success_non_empty"
    assert row["duration_load_ms"] is not None
    summary = json.loads(row["result_summary_json"])
    assert summary["upstream_count"] == 2


def test_no_telemetry_flag_skips_write(tmp_path, monkeypatch):
    db = tmp_path / "telemetry.sqlite3"
    out = _bootstrap(tmp_path / "dump")
    monkeypatch.setenv("ODOO_GRAPH_TELEMETRY", "1")
    monkeypatch.setenv("ODOO_GRAPH_TELEMETRY_DB", str(db))

    rc = main(["model", "res.partner", "--out-dir", out, "--no-telemetry"])

    assert rc == 0
    assert fetch_invocations(db) == []


def test_report_detects_fanout_batch_and_gap_sensitivity(tmp_path):
    db = tmp_path / "telemetry.sqlite3"
    insert_invocation(_row(
        command="path",
        started_at="2026-05-29T00:00:00.000Z",
        start_raw="model.a",
        target_raw="model.b.x",
        target_model="model.b",
        target_field="x",
        max_depth=6,
        max_paths=3,
        duration_load_ms=2500,
        extra_json={"graph_cache_key": "dump-1"},
    ), db)
    insert_invocation(_row(
        command="path",
        started_at="2026-05-29T00:00:10.000Z",
        start_raw="model.a",
        target_raw="model.c.y",
        target_model="model.c",
        target_field="y",
        max_depth=6,
        max_paths=3,
        duration_load_ms=2500,
        extra_json={"graph_cache_key": "dump-1"},
    ), db)
    insert_invocation(_row(
        command="field",
        started_at="2026-05-29T00:00:20.000Z",
        target_raw="model.b.supplier_id",
        target_model="model.b",
        target_field="supplier_id",
    ), db)
    insert_invocation(_row(
        command="field",
        started_at="2026-05-29T00:00:30.000Z",
        target_raw="model.c.supplier_id",
        target_model="model.c",
        target_field="supplier_id",
    ), db)
    insert_invocation(_row(
        command="model",
        started_at="2026-05-29T00:02:30.000Z",
        target_raw="model.d",
        target_kind="model",
        target_model="model.d",
        target_field=None,
    ), db)

    report = build_report(str(db), gap_seconds=60)
    analysis = report["analysis"]

    assert analysis["session_metrics"]["session_count"] == 2
    assert report["sensitivity"]["30"]["session_count"] == 2
    assert analysis["path_fanout"]["group_count"] == 1
    assert analysis["path_fanout"]["groups"][0]["distinct_targets"] == 2
    groups = analysis["batch_exploration"]["same_field_cross_model_groups"]
    assert groups[0]["target_field"] == "supplier_id"
    assert groups[0]["distinct_models"] == 2
    assert analysis["load_overhead"]["same_graph_repeated_load_count"] == 1
