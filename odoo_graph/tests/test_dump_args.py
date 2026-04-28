"""Make sure dump.py passes -c through to odoo-bin AND its own CLI flags still
take precedence. We stub subprocess.run and never really launch Odoo.
"""
import os
from pathlib import Path
from unittest import mock

import pytest

from odoo_graph import dump as dump_module


class _FakeProc:
    def __init__(self):
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""


def _setup_fake_odoo(tmp_path: Path) -> Path:
    odoo_root = tmp_path / "odoo"
    (odoo_root / "addons").mkdir(parents=True)
    (odoo_root / "odoo-bin").write_text("#!/usr/bin/env python\n")
    (odoo_root / "odoo-bin").chmod(0o755)
    return odoo_root


def test_dump_passes_config_flag_to_odoo_bin(tmp_path):
    odoo_root = _setup_fake_odoo(tmp_path)
    out = tmp_path / "out"
    conf = tmp_path / "odoo.conf"
    conf.write_text("[options]\n", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        # Write summary so dump() doesn't bail out before resolve.
        Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]).mkdir(parents=True, exist_ok=True)
        (Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]) / "summary.json").write_text("{}")
        (Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]) / "nodes.jsonl").write_text("")
        (Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]) / "edges.jsonl").write_text("")
        fake_run.captured_cmd = cmd
        return _FakeProc()

    with mock.patch("odoo_graph.dump.subprocess.run", side_effect=fake_run):
        dump_module.dump(
            database="mydb",
            odoo_path=str(odoo_root),
            config_file=str(conf),
            out_dir=str(out),
            db_host="h", db_port=5432, db_user="u", db_password=None,
        )

    cmd = fake_run.captured_cmd
    # -c must appear BEFORE -d so odoo-bin treats it as a global option and
    # our explicit flags still override the conf.
    assert "-c" in cmd
    c_idx = cmd.index("-c")
    d_idx = cmd.index("-d")
    assert c_idx < d_idx, f"-c must precede -d; got: {cmd}"
    assert cmd[c_idx + 1] == str(conf.resolve())


def test_dump_without_config_does_not_pass_c(tmp_path):
    odoo_root = _setup_fake_odoo(tmp_path)
    out = tmp_path / "out"

    def fake_run(cmd, **kwargs):
        Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]).mkdir(parents=True, exist_ok=True)
        (Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]) / "summary.json").write_text("{}")
        (Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]) / "nodes.jsonl").write_text("")
        (Path(kwargs["env"]["ODOO_GRAPH_OUT_DIR"]) / "edges.jsonl").write_text("")
        fake_run.captured_cmd = cmd
        return _FakeProc()

    with mock.patch("odoo_graph.dump.subprocess.run", side_effect=fake_run):
        dump_module.dump(
            database="mydb",
            odoo_path=str(odoo_root),
            out_dir=str(out),
            db_host="h", db_port=5432, db_user="u", db_password="p",
        )

    assert "-c" not in fake_run.captured_cmd


def test_dump_fails_when_odoo_bin_missing(tmp_path):
    with pytest.raises(dump_module.DumpError):
        dump_module.dump(
            database="mydb",
            odoo_path=str(tmp_path),  # no odoo-bin here
            out_dir=str(tmp_path / "out"),
        )
