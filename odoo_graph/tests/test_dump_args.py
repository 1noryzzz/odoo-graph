"""Make sure dump.py passes -c through to odoo-bin AND its own CLI flags still
take precedence. We stub subprocess.run and never really launch Odoo.
"""
import json
import os
from pathlib import Path
from unittest import mock

import pytest

from odoo_graph import __version__
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
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["database"] == "mydb"
    assert meta["odoo_path"] == str(odoo_root.resolve())
    assert meta["cwd"] == str(Path.cwd().resolve())
    assert meta["package_version"] == __version__
    assert meta["generated_at"].endswith("Z")


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


def test_resolve_odoo_path_uses_first_valid_candidate(tmp_path):
    (tmp_path / "odoo-bin").write_text("", encoding="utf-8")
    _setup_fake_odoo(tmp_path)

    resolution = dump_module.resolve_odoo_path(
        None,
        source="auto",
        cwd=tmp_path,
    )

    assert resolution.path == str(tmp_path.resolve())
    assert resolution.source == "auto"
    assert resolution.candidate == "."


def test_resolve_explicit_invalid_path_does_not_fall_through(tmp_path):
    _setup_fake_odoo(tmp_path)

    with pytest.raises(dump_module.OdooPathResolutionError) as exc_info:
        dump_module.resolve_odoo_path(
            "./missing",
            source="cli",
            cwd=tmp_path,
        )

    error = exc_info.value
    assert error.reason == "invalid_cli_path"
    assert error.found_candidate == "./odoo"
    assert error.checked == dump_module.ODOO_PATH_CANDIDATES
    assert "Unable to resolve Odoo source path" in str(error)
    assert "Found:\n  ./odoo/odoo-bin" in str(error)


def test_resolve_odoo_path_reports_all_candidates_missing(tmp_path):
    with pytest.raises(dump_module.OdooPathResolutionError) as exc_info:
        dump_module.resolve_odoo_path(None, source="auto", cwd=tmp_path)

    assert exc_info.value.reason == "no_candidate"
    assert exc_info.value.found_candidate is None
    for candidate in dump_module.ODOO_PATH_CANDIDATES:
        assert f"  {candidate}" in str(exc_info.value)
