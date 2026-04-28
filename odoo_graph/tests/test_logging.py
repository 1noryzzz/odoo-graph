"""Logging behaviour: levels, env var, idempotent setup, stderr-only output."""
from __future__ import annotations

import json
import logging

import pytest

from odoo_graph.cli import main
from odoo_graph.logging import get_logger, setup_logging
from odoo_graph.resolve import resolve_paths
from odoo_graph.tests.fixtures import build_fixture


def _bootstrap(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    return str(tmp_path)


@pytest.fixture(autouse=True)
def _reset_logger():
    """Each test gets a clean logger so state doesn't leak."""
    yield
    log = logging.getLogger("odoo_graph")
    for h in list(log.handlers):
        if getattr(h, "_odoo_graph_owned", False):
            log.removeHandler(h)
    log.setLevel(logging.WARNING)


def test_setup_logging_default_is_info():
    log = setup_logging()
    assert log.level == logging.INFO


def test_setup_logging_explicit_level_string():
    log = setup_logging(level="DEBUG")
    assert log.level == logging.DEBUG


def test_setup_logging_verbose_count_promotes_to_debug():
    log = setup_logging(verbosity=1)
    assert log.level == logging.DEBUG


def test_env_var_controls_level(monkeypatch):
    monkeypatch.setenv("ODOO_GRAPH_LOG", "WARNING")
    log = setup_logging()
    assert log.level == logging.WARNING


def test_setup_logging_is_idempotent_no_handler_duplication():
    setup_logging(level="INFO")
    setup_logging(level="DEBUG")
    log = logging.getLogger("odoo_graph")
    owned = [h for h in log.handlers if getattr(h, "_odoo_graph_owned", False)]
    assert len(owned) == 1


def test_get_logger_returns_namespaced_child():
    parent = setup_logging()
    child = get_logger("odoo_graph.tests.subpkg")
    assert child.name == "odoo_graph.tests.subpkg"
    # Effective level inherits from parent.
    assert child.getEffectiveLevel() == parent.level


def test_cli_quiet_silences_info_keeps_errors(tmp_path, capsys):
    out = _bootstrap(tmp_path)
    rc = main(["-q", "field", "res.partner.display_name", "--out-dir", out, "-f", "json"])
    assert rc == 0
    err = capsys.readouterr().err
    # No INFO-level lines (e.g. "field ...: 2 upstream / ...").
    assert "field res.partner.display_name" not in err
    # stdout still has the JSON payload.


def test_cli_default_info_logs_command_summary(tmp_path, capsys):
    out = _bootstrap(tmp_path)
    rc = main(["field", "res.partner.display_name", "--out-dir", out, "-f", "json"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "field res.partner.display_name" in err
    assert "upstream" in err and "downstream" in err


def test_cli_verbose_emits_debug(tmp_path, capsys):
    out = _bootstrap(tmp_path)
    rc = main(["-v", "field", "res.partner.display_name", "--out-dir", out, "-f", "json"])
    assert rc == 0
    err = capsys.readouterr().err
    # Debug lines from cli + graph load.
    assert "DEBUG" in err
    assert "loading dump from" in err
    assert "graph loaded" in err  # INFO from graph too


def test_logs_go_to_stderr_not_stdout(tmp_path, capsys):
    """Critical for `... -f json | jq`: stdout must stay clean."""
    out = _bootstrap(tmp_path)
    rc = main(["field", "res.partner.display_name", "--out-dir", out, "-f", "json"])
    assert rc == 0
    captured = capsys.readouterr()
    # stdout should parse as JSON (no log noise mixed in).
    parsed = json.loads(captured.out)
    assert parsed["field"]["model"] == "res.partner"


def test_log_level_warning_hides_info_lines(tmp_path, capsys):
    out = _bootstrap(tmp_path)
    rc = main([
        "--log-level", "WARNING",
        "model", "res.partner", "--out-dir", out, "-f", "json",
    ])
    assert rc == 0
    err = capsys.readouterr().err
    # The "model res.partner: extended by ..." INFO line should be gone.
    assert "extended by" not in err
