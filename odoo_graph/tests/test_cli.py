import json
from unittest import mock

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


def test_cli_field_works_with_dotted_model_name(capsys, tmp_path):
    """Real-world: ifs.gar.partner.supplier.merchant has 4 dots in the name.
    The splitter must match the longest model prefix, not just rpartition.
    """
    out = _bootstrap(tmp_path)
    rc = main([
        "field",
        "ifs.gar.partner.supplier.merchant.t18_contract_info_id",
        "--out-dir", out, "-f", "json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["field"]["model"] == "ifs.gar.partner.supplier.merchant"
    assert payload["field"]["name"] == "t18_contract_info_id"


def test_cli_typo_dropped_dot_gives_helpful_suggestion(capsys, tmp_path):
    """Reproduces the user-reported case: 'merchant' and 't18...' run together
    because a dot was dropped. We should recognise the closest model and
    suggest fix candidates instead of the cryptic 'Field not found'.
    """
    out = _bootstrap(tmp_path)
    rc = main([
        "field",
        # Exactly the input the user pasted, minus the missing '.' between
        # 'merchant' and 't18_contract_info_id'.
        "ifs.gar.partner.supplier.merchantt18_contract_info_id",
        "--out-dir", out,
    ])
    assert rc == 1
    err = capsys.readouterr().err
    # We can't recognise a model prefix here (the merged token breaks the chain).
    # So we should at least suggest models close to the typo.
    assert "did you mean" in err or "no model matches" in err
    # And we shouldn't pretend the model is real.
    assert "ifs.gar.partner.supplier.merchant" in err


def test_cli_field_typo_after_real_model_suggests_fields(capsys, tmp_path):
    """When the model is correct but the field has a typo, suggestions should
    list close field names on that model.
    """
    out = _bootstrap(tmp_path)
    rc = main([
        "field",
        "ifs.gar.partner.supplier.merchant.t18_contract_info",  # missing _id
        "--out-dir", out,
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "recognised model: ifs.gar.partner.supplier.merchant" in err
    assert "t18_contract_info_id" in err  # the real field name


def test_cli_unknown_model_suggests_close_models(capsys, tmp_path):
    out = _bootstrap(tmp_path)
    rc = main(["model", "res.parner", "--out-dir", out])  # typo: parner
    assert rc == 1
    err = capsys.readouterr().err
    assert "did you mean" in err
    assert "res.partner" in err


def test_cli_requires_out_dir_or_db(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["field", "res.partner.name"])
    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "need --out-dir" in err


def test_dump_reads_config_for_connection_and_addons(tmp_path, capsys):
    """`odoo-graph dump -c odoo.conf -d mydb` should pull db_host/port/user/
    password and addons_path from the conf file, and pass -c through to
    `odoo-bin`. We intercept dump_registry to inspect the effective kwargs.
    """
    (tmp_path / "addons-oabay").mkdir()
    conf = tmp_path / "odoo.conf"
    conf.write_text(
        "[options]\n"
        "db_host = 192.168.1.10\n"
        "db_port = 5433\n"
        "db_user = erp\n"
        "db_password = s3cret\n"
        "addons_path = addons-oabay\n",
        encoding="utf-8",
    )

    captured = {}

    def fake_dump(**kw):
        captured.update(kw)
        return {
            "out_dir": str(tmp_path / "out"),
            "summary": {
                "models": 0, "abstract_models": 0, "transient_models": 0,
                "fields": 0, "fields_multi_module": 0, "fields_computed": 0,
                "fields_related": 0, "fields_inherited_delegate": 0,
                "methods_with_overrides": 0, "edges_depends_field": 0,
                "edges_method_overrides": 0,
            },
            "resolve": {"resolved": 0, "unresolved": 0},
            "stderr_tail": "",
        }

    with mock.patch("odoo_graph.cli.dump_registry", side_effect=fake_dump):
        rc = main([
            "dump", "-c", str(conf), "-d", "mydb",
            "--odoo-path", str(tmp_path),  # not actually run
            "-f", "json",
        ])
    assert rc == 0
    assert captured["database"] == "mydb"
    assert captured["db_host"] == "192.168.1.10"
    assert captured["db_port"] == 5433
    assert captured["db_user"] == "erp"
    assert captured["db_password"] == "s3cret"
    assert captured["config_file"] == str(conf)
    # addons_path resolved against conf dir
    assert str(tmp_path / "addons-oabay") in captured["addons_path"]


def test_dump_cli_flag_wins_over_config(tmp_path):
    """Explicit --db-host on CLI should beat a value in the conf file."""
    conf = tmp_path / "odoo.conf"
    conf.write_text("[options]\ndb_host = from-conf\n", encoding="utf-8")

    captured = {}

    def fake_dump(**kw):
        captured.update(kw)
        return {
            "out_dir": "x", "summary": {
                "models": 0, "abstract_models": 0, "transient_models": 0,
                "fields": 0, "fields_multi_module": 0, "fields_computed": 0,
                "fields_related": 0, "fields_inherited_delegate": 0,
                "methods_with_overrides": 0, "edges_depends_field": 0,
                "edges_method_overrides": 0,
            },
            "resolve": {"resolved": 0, "unresolved": 0}, "stderr_tail": "",
        }

    with mock.patch("odoo_graph.cli.dump_registry", side_effect=fake_dump):
        rc = main([
            "dump", "-c", str(conf), "-d", "mydb",
            "--db-host", "from-cli",
            "--odoo-path", str(tmp_path),
        ])
    assert rc == 0
    assert captured["db_host"] == "from-cli"


def test_dump_requires_db_name_from_somewhere(tmp_path, capsys):
    conf = tmp_path / "odoo.conf"
    conf.write_text("[options]\ndb_host = h\n", encoding="utf-8")

    with mock.patch("odoo_graph.cli.dump_registry") as m:
        rc = main(["dump", "-c", str(conf), "--odoo-path", str(tmp_path)])
    assert rc == 2
    m.assert_not_called()
    err = capsys.readouterr().err
    assert "database name required" in err


def test_dump_db_name_can_come_from_config(tmp_path):
    conf = tmp_path / "odoo.conf"
    conf.write_text(
        "[options]\ndb_name = from-conf\ndb_host = h\n", encoding="utf-8"
    )

    captured = {}

    def fake_dump(**kw):
        captured.update(kw)
        return {
            "out_dir": "x", "summary": {
                "models": 0, "abstract_models": 0, "transient_models": 0,
                "fields": 0, "fields_multi_module": 0, "fields_computed": 0,
                "fields_related": 0, "fields_inherited_delegate": 0,
                "methods_with_overrides": 0, "edges_depends_field": 0,
                "edges_method_overrides": 0,
            },
            "resolve": {"resolved": 0, "unresolved": 0}, "stderr_tail": "",
        }

    with mock.patch("odoo_graph.cli.dump_registry", side_effect=fake_dump):
        rc = main(["dump", "-c", str(conf), "--odoo-path", str(tmp_path)])
    assert rc == 0
    assert captured["database"] == "from-conf"
