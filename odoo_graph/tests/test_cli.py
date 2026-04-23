import json

import pytest

from odoo_graph.cli import main
from odoo_graph.resolve import resolve_paths
from odoo_graph.tests.fixtures import build_fixture


def _bootstrap(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    return str(tmp_path)


def test_cli_field_json(capsys, tmp_path):
    out = _bootstrap(tmp_path)
    rc = main(["field", "res.partner.display_name", "--out-dir", out, "-f", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["field"]["name"] == "display_name"


def test_cli_model_human(capsys, tmp_path):
    out = _bootstrap(tmp_path)
    rc = main(["model", "res.partner", "--out-dir", out])
    assert rc == 0
    text = capsys.readouterr().out
    assert "res.partner" in text
    assert "Fields by module" in text


def test_cli_impact(capsys, tmp_path):
    out = _bootstrap(tmp_path)
    rc = main(["impact", "res.partner.name", "--out-dir", out, "-f", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert any("display_name" in h["field"] for h in payload["impacted"])


def test_cli_overrides(capsys, tmp_path):
    out = _bootstrap(tmp_path)
    rc = main(["overrides", "res.partner.write", "--out-dir", out, "-f", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["override_depth"] == 3


def test_cli_unknown_target_exits_non_zero(capsys, tmp_path):
    out = _bootstrap(tmp_path)
    rc = main(["field", "res.partner.not_a_field", "--out-dir", out])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Field not found" in err


def test_cli_requires_out_dir_or_db(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["field", "res.partner.name"])
    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "need --out-dir" in err
