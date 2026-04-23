"""`odoo-graph` CLI entry point."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .dump import DumpError, _default_cache_dir, dump as dump_registry
from .formatters import FORMATS, emit
from .graph import OdooGraph, load_graph


def _add_common_query_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--out-dir", "-o", default=None,
        help="Dump directory. Default: ~/.cache/odoo-graph/<db>/, "
             "auto-detected from --db or $ODOO_GRAPH_OUT_DIR if unset.",
    )
    p.add_argument(
        "--db", default=os.environ.get("ODOO_GRAPH_DB"),
        help="Database name to resolve default --out-dir (or $ODOO_GRAPH_DB).",
    )
    p.add_argument(
        "--format", "-f", choices=FORMATS, default="human",
        help="Output format (default: human).",
    )


def _resolve_out_dir(args: argparse.Namespace) -> str:
    if args.out_dir:
        return args.out_dir
    env = os.environ.get("ODOO_GRAPH_OUT_DIR")
    if env:
        return env
    if args.db:
        return str(_default_cache_dir(args.db))
    print(
        "[odoo-graph] need --out-dir, --db, or $ODOO_GRAPH_DB to locate the dump",
        file=sys.stderr,
    )
    sys.exit(2)


def _load(args: argparse.Namespace) -> OdooGraph:
    return load_graph(_resolve_out_dir(args))


# ---------- subcommands ----------------------------------------------------

def cmd_dump(args: argparse.Namespace) -> int:
    try:
        result = dump_registry(
            database=args.database,
            odoo_path=args.odoo_path,
            addons_path=args.addons_path or None,
            db_host=args.db_host,
            db_port=args.db_port,
            db_user=args.db_user,
            db_password=args.db_password,
            out_dir=args.out_dir,
        )
    except DumpError as exc:
        print(f"[odoo-graph] dump failed: {exc}", file=sys.stderr)
        return 1
    emit(result, kind="dump", fmt=args.format)
    return 0


def cmd_field(args: argparse.Namespace) -> int:
    g = _load(args)
    model, _, name = args.target.rpartition(".")
    if not model:
        print("[odoo-graph] field target must be 'model.field'", file=sys.stderr)
        return 2
    try:
        payload = g.field_lineage(model, name)
    except KeyError as exc:
        print(f"[odoo-graph] {exc}", file=sys.stderr)
        return 1
    emit(payload, kind="field", fmt=args.format)
    return 0


def cmd_model(args: argparse.Namespace) -> int:
    g = _load(args)
    try:
        payload = g.model_summary(args.target)
    except KeyError as exc:
        print(f"[odoo-graph] {exc}", file=sys.stderr)
        return 1
    emit(payload, kind="model", fmt=args.format)
    return 0


def cmd_module(args: argparse.Namespace) -> int:
    g = _load(args)
    try:
        payload = g.module_summary(args.target)
    except KeyError as exc:
        print(f"[odoo-graph] {exc}", file=sys.stderr)
        return 1
    emit(payload, kind="module", fmt=args.format)
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    g = _load(args)
    model, _, name = args.target.rpartition(".")
    if not model:
        print("[odoo-graph] impact target must be 'model.field'", file=sys.stderr)
        return 2
    try:
        hits = g.impact(model, name, max_depth=args.max_depth)
    except KeyError as exc:
        print(f"[odoo-graph] {exc}", file=sys.stderr)
        return 1
    emit(
        {"target": {"model": model, "name": name},
         "max_depth": args.max_depth, "impacted": hits},
        kind="impact", fmt=args.format,
    )
    return 0


def cmd_overrides(args: argparse.Namespace) -> int:
    g = _load(args)
    model, _, method = args.target.rpartition(".")
    if not model:
        print("[odoo-graph] overrides target must be 'model.method'", file=sys.stderr)
        return 2
    try:
        payload = g.overrides_of(model, method)
    except KeyError as exc:
        print(f"[odoo-graph] {exc}", file=sys.stderr)
        return 1
    emit(payload, kind="overrides", fmt=args.format)
    return 0


# ---------- parser ---------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="odoo-graph")
    p.add_argument("--version", action="version", version=f"odoo-graph {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    # dump
    pd = sub.add_parser("dump", help="Run Odoo and dump the registry graph.")
    pd.add_argument("-d", "--database", required=True, help="Odoo database name")
    pd.add_argument("--odoo-path", default=os.environ.get("ODOO_PATH", "./odoo-17.0"),
                    help="Path to Odoo source tree (contains odoo-bin). "
                         "Default: $ODOO_PATH or ./odoo-17.0")
    pd.add_argument("--addons-path", action="append", default=[],
                    help="Extra addons dir (repeatable)")
    pd.add_argument("--db-host", default="127.0.0.1")
    pd.add_argument("--db-port", type=int, default=5432)
    pd.add_argument("--db-user", "-r", default="odoo")
    pd.add_argument("--db-password", "-w", default=os.environ.get("PGPASSWORD", "odoo"))
    pd.add_argument("--out-dir", "-o", default=None,
                    help="Defaults to ~/.cache/odoo-graph/<db>/")
    pd.add_argument("--format", "-f", choices=FORMATS, default="human")
    pd.set_defaults(func=cmd_dump)

    # field
    pf = sub.add_parser("field", help="Lineage (upstream/downstream) for a field.")
    pf.add_argument("target", help="model.field, e.g. res.partner.name")
    _add_common_query_args(pf)
    pf.set_defaults(func=cmd_field)

    # model
    pm = sub.add_parser("model", help="Summary of a model (inheritance + field breakdown).")
    pm.add_argument("target", help="model name, e.g. res.partner")
    _add_common_query_args(pm)
    pm.set_defaults(func=cmd_model)

    # module
    pmod = sub.add_parser("module", help="Summary of a module (defined vs extended).")
    pmod.add_argument("target", help="module name, e.g. mail")
    _add_common_query_args(pmod)
    pmod.set_defaults(func=cmd_module)

    # impact
    pi = sub.add_parser("impact", help="Downstream recompute impact of a field.")
    pi.add_argument("target", help="model.field")
    pi.add_argument("--max-depth", type=int, default=3)
    _add_common_query_args(pi)
    pi.set_defaults(func=cmd_impact)

    # overrides
    po = sub.add_parser("overrides", help="Override chain of a method.")
    po.add_argument("target", help="model.method, e.g. res.users.write")
    _add_common_query_args(po)
    po.set_defaults(func=cmd_overrides)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
