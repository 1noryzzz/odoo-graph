"""Parse Odoo-style config files (``odoo.conf`` / ``~/.odoorc``).

We only need a subset: connection + addons_path + odoo root. We read the
``[options]`` section with configparser, matching Odoo's own parsing (see
``odoo/tools/config.py``). Comments, booleans and missing sections are
handled the same way.
"""
from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# Keys we care about. Everything else is ignored (but harmless to have).
KEYS_CONN = ("db_host", "db_port", "db_user", "db_password", "db_name")
KEY_ADDONS = "addons_path"


@dataclass
class ConfigValues:
    """Subset of Odoo config options relevant to odoo-graph."""

    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = None
    addons_path: List[str] = field(default_factory=list)
    source_path: Optional[str] = None


def _clean(val: str) -> str:
    # Odoo treats the literal strings True/False specially; connection fields
    # are always strings, so only strip quotes/whitespace.
    v = val.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v


def load_config(path: str | os.PathLike) -> ConfigValues:
    """Read an Odoo config file and extract the keys we use.

    Unknown values are silently ignored. Missing file -> FileNotFoundError.
    """
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Odoo config file not found: {p}")

    parser = configparser.RawConfigParser()
    # Be tolerant: some Odoo confs have BOMs / tabs; RawConfigParser is lenient.
    parser.read([str(p)], encoding="utf-8")

    values = ConfigValues(source_path=str(p))
    if not parser.has_section("options"):
        return values

    opts = {k: _clean(v) for k, v in parser.items("options")}

    if "db_host" in opts and opts["db_host"] not in ("False", "false", ""):
        values.db_host = opts["db_host"]
    if "db_port" in opts and opts["db_port"] not in ("False", "false", ""):
        try:
            values.db_port = int(opts["db_port"])
        except ValueError:
            # Odoo stores 'False' when unset — we already filtered, but be safe
            values.db_port = None
    if "db_user" in opts and opts["db_user"] not in ("False", "false", ""):
        values.db_user = opts["db_user"]
    if "db_password" in opts and opts["db_password"] not in ("False", "false", ""):
        values.db_password = opts["db_password"]
    if "db_name" in opts and opts["db_name"] not in ("False", "false", ""):
        values.db_name = opts["db_name"]
    if KEY_ADDONS in opts and opts[KEY_ADDONS]:
        # Odoo: comma-separated list of dirs. Relative paths are resolved
        # against the conf file's parent (Odoo's own behavior via abspath).
        raw = opts[KEY_ADDONS]
        base = p.parent
        parts: List[str] = []
        for item in raw.split(","):
            item = item.strip()
            if not item:
                continue
            ip = Path(item).expanduser()
            if not ip.is_absolute():
                ip = (base / ip).resolve()
            parts.append(str(ip))
        values.addons_path = parts

    return values


def merge(cli: ConfigValues, conf: ConfigValues) -> ConfigValues:
    """CLI flags win over conf file values; conf wins over nothing.

    Addons paths are unioned (CLI first, then conf, de-duped, order preserved).
    """
    seen: set = set()
    merged_addons: List[str] = []
    for src in (cli.addons_path, conf.addons_path):
        for a in src:
            if a not in seen:
                seen.add(a)
                merged_addons.append(a)

    return ConfigValues(
        db_host=cli.db_host or conf.db_host,
        db_port=cli.db_port or conf.db_port,
        db_user=cli.db_user or conf.db_user,
        db_password=cli.db_password or conf.db_password,
        db_name=cli.db_name or conf.db_name,
        addons_path=merged_addons,
        source_path=conf.source_path,
    )
