"""Dump driver: spawn `odoo-bin shell`, feed the probe script, then resolve.

The probe itself lives in `_probe_script.py` because it runs inside Odoo's
Python (via `odoo-bin shell <stdin>`). This module stays in the host Python
and wires subprocess + environment.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .resolve import resolve_paths

_PROBE_SCRIPT = Path(__file__).with_name("_probe_script.py")


class DumpError(RuntimeError):
    pass


def _default_cache_dir(db: str) -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "odoo-graph" / db


def _abs_str(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def dump(
    database: str,
    *,
    odoo_path: str,
    addons_path: Optional[Iterable[str]] = None,
    db_host: str = "127.0.0.1",
    db_port: int = 5432,
    db_user: str = "odoo",
    db_password: Optional[str] = "odoo",
    config_file: Optional[str] = None,
    out_dir: Optional[str] = None,
    python_exe: Optional[str] = None,
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Run Odoo shell and dump registry metadata to `out_dir`.

    Args:
        database: Odoo DB name to connect to (must be already initialized).
        odoo_path: Path to the Odoo source tree (contains odoo-bin).
        addons_path: Optional extra addons dirs. The default Odoo `addons/`
            is always added if `odoo_path/addons` exists.
        db_host/db_port/db_user/db_password: Postgres connection.
        config_file: Optional odoo.conf. When set, passed through to `odoo-bin
            -c <file>` so Odoo itself also reads all other options
            (data_dir, log settings, unoconv, etc.). The caller should have
            already merged its connection/addons values into the args above.
        out_dir: Where to write JSONL. Defaults to ~/.cache/odoo-graph/<db>/.
        python_exe: Python interpreter to use (defaults to current sys.executable).
        extra_env: Extra env vars passed to subprocess.

    Returns:
        dict with keys: out_dir, summary (json from summary.json), resolve
        (counts), stderr_tail (last ~20 lines of stderr).
    """
    odoo_root = _abs_str(odoo_path)
    if not os.path.isfile(os.path.join(odoo_root, "odoo-bin")):
        raise DumpError(f"odoo-bin not found under {odoo_root}")

    if out_dir is None:
        out = _default_cache_dir(database)
    else:
        out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    addons_list: List[str] = []
    default_addons = Path(odoo_root) / "addons"
    if default_addons.exists():
        addons_list.append(str(default_addons))
    if addons_path:
        for p in addons_path:
            absp = _abs_str(p)
            if absp not in addons_list:
                addons_list.append(absp)

    py = python_exe or sys.executable
    cmd = [
        py,
        os.path.join(odoo_root, "odoo-bin"),
        "shell",
    ]
    if config_file:
        # Let odoo-bin read the same file too. CLI flags below will override
        # anything in the conf, so explicit values stay authoritative.
        cmd += ["-c", _abs_str(config_file)]
    cmd += [
        "-d", database,
        "--db_host", db_host,
        "--db_port", str(db_port),
        "-r", db_user,
        "--no-http",
        "--addons-path", ",".join(addons_list),
    ]
    if db_password is not None:
        cmd += ["-w", db_password]

    env = os.environ.copy()
    env["ODOO_GRAPH_OUT_DIR"] = str(out)
    env.setdefault("PGPASSWORD", db_password or "")
    py_path_parts = [odoo_root]
    if env.get("PYTHONPATH"):
        py_path_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(py_path_parts)
    if extra_env:
        env.update(extra_env)

    script = _PROBE_SCRIPT.read_text(encoding="utf-8")

    print(f"[odoo-graph] $ {' '.join(shlex.quote(c) for c in cmd)}", file=sys.stderr)
    proc = subprocess.run(
        cmd, input=script, text=True, env=env,
        capture_output=True,
    )
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-30:])
        raise DumpError(
            f"odoo-bin shell exited {proc.returncode}\n--- stderr tail ---\n{tail}"
        )

    summary_path = out / "summary.json"
    if not summary_path.exists():
        tail = "\n".join(proc.stderr.splitlines()[-30:])
        raise DumpError(f"probe did not write summary.json\n--- stderr tail ---\n{tail}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    resolve_counts = resolve_paths(str(out))

    meta = {
        "database": database,
        "odoo_path": odoo_root,
        "addons_path": addons_list,
        "out_dir": str(out),
        "summary": summary,
        "resolve": resolve_counts,
    }
    (out / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Keep the tail of odoo stderr so callers can show it.
    stderr_tail = "\n".join(proc.stderr.splitlines()[-20:])
    return {
        "out_dir": str(out),
        "summary": summary,
        "resolve": resolve_counts,
        "stderr_tail": stderr_tail,
    }
