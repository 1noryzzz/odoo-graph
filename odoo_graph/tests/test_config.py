import configparser
import os
from pathlib import Path

import pytest

from odoo_graph.config import ConfigValues, load_config, merge


def _write_conf(tmp_path: Path, body: str, name: str = "odoo.conf") -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_load_basic_options(tmp_path):
    conf = _write_conf(tmp_path, """
[options]
db_host = 10.0.0.1
db_port = 5433
db_user = admin
db_password = s3cret
db_name = prod
""")
    vals = load_config(conf)
    assert vals.db_host == "10.0.0.1"
    assert vals.db_port == 5433
    assert vals.db_user == "admin"
    assert vals.db_password == "s3cret"
    assert vals.db_name == "prod"
    assert vals.source_path == str(conf)


def test_load_false_string_treated_as_unset(tmp_path):
    conf = _write_conf(tmp_path, """
[options]
db_host = False
db_password = false
db_port = False
""")
    vals = load_config(conf)
    assert vals.db_host is None
    assert vals.db_password is None
    assert vals.db_port is None


def test_addons_path_relative_resolves_against_conf_dir(tmp_path):
    (tmp_path / "addons-oabay").mkdir()
    (tmp_path / "custom").mkdir()
    conf = _write_conf(tmp_path, f"""
[options]
addons_path = addons-oabay,{tmp_path / 'custom'},./not-there
""")
    vals = load_config(conf)
    # Relative 'addons-oabay' must resolve to tmp_path/addons-oabay
    assert str(tmp_path / "addons-oabay") in vals.addons_path
    # Absolute path passes through
    assert str(tmp_path / "custom") in vals.addons_path
    # './not-there' resolves even if it doesn't exist yet (lazy validation)
    assert any(p.endswith("not-there") for p in vals.addons_path)


def test_missing_options_section_is_ok(tmp_path):
    conf = _write_conf(tmp_path, "")
    vals = load_config(conf)
    assert vals.db_host is None
    assert vals.addons_path == []


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.conf")


def test_quoted_values_are_stripped(tmp_path):
    conf = _write_conf(tmp_path, """
[options]
db_user = "admin"
db_password = 'p@ss'
""")
    vals = load_config(conf)
    assert vals.db_user == "admin"
    assert vals.db_password == "p@ss"


def test_merge_cli_overrides_conf(tmp_path):
    cli = ConfigValues(db_host="cli-host", db_user=None, db_name="overridden",
                       addons_path=["/cli/one"])
    conf = ConfigValues(db_host="conf-host", db_port=5433, db_user="admin",
                        db_name="from-conf", addons_path=["/conf/a", "/cli/one"])
    m = merge(cli, conf)
    assert m.db_host == "cli-host"
    assert m.db_port == 5433
    assert m.db_user == "admin"
    assert m.db_name == "overridden"
    # de-dup preserves CLI-first order then adds conf extras
    assert m.addons_path == ["/cli/one", "/conf/a"]


def test_merge_empty_cli_inherits_conf(tmp_path):
    cli = ConfigValues()
    conf = ConfigValues(db_host="h", db_port=5432, db_name="d",
                        addons_path=["/a"])
    m = merge(cli, conf)
    assert m.db_host == "h"
    assert m.db_port == 5432
    assert m.db_name == "d"
    assert m.addons_path == ["/a"]


def test_integration_configparser_shape(tmp_path):
    # Confirm the parser we use agrees with Odoo's own RawConfigParser
    conf = _write_conf(tmp_path, """
[options]
; a comment like the ones in real odoo.conf
db_host = localhost
addons_path = /opt/odoo/addons
""")
    raw = configparser.RawConfigParser()
    raw.read([str(conf)])
    assert raw.has_section("options")
    assert raw.get("options", "db_host") == "localhost"
    vals = load_config(conf)
    assert vals.db_host == "localhost"
    assert vals.addons_path == ["/opt/odoo/addons"]
