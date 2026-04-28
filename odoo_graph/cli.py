"""`odoo-graph` CLI entry point."""
from __future__ import annotations

import argparse
import difflib
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from . import __version__
from .config import ConfigValues, load_config, merge
from .dump import DumpError, _default_cache_dir, dump as dump_registry
from .formatters import FORMATS, emit
from .graph import OdooGraph, load_graph
from .logging import get_logger, setup_logging

log = get_logger(__name__)


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
        log.debug("resolved out_dir from --out-dir: %s", args.out_dir)
        return args.out_dir
    env = os.environ.get("ODOO_GRAPH_OUT_DIR")
    if env:
        log.debug("resolved out_dir from $ODOO_GRAPH_OUT_DIR: %s", env)
        return env
    if args.db:
        d = str(_default_cache_dir(args.db))
        log.debug("resolved out_dir from --db default cache: %s", d)
        return d
    log.error(
        "need --out-dir, --db, or $ODOO_GRAPH_DB to locate the dump"
    )
    sys.exit(2)


def _load(args: argparse.Namespace) -> OdooGraph:
    return load_graph(_resolve_out_dir(args))


def _split_model_field(g: OdooGraph, target: str) -> Tuple[str, str]:
    """Split 'model.field' robustly even when the model name contains dots.

    Strategy: walk every '.' position from the right; the first split where
    the left side matches a real model node wins. If none match, we still
    fall back to rpartition() so the downstream "field not found" handler
    can suggest similar names.
    """
    parts = target.split(".")
    if len(parts) < 2:
        return ("", target)
    for i in range(len(parts) - 1, 0, -1):
        candidate_model = ".".join(parts[:i])
        if g.node(g.model_id(candidate_model)) is not None:
            return (candidate_model, ".".join(parts[i:]))
    # No real model matched — return rpartition split as best guess.
    model, _, name = target.rpartition(".")
    return (model, name)


def _suggest(label: str, candidates: list, want: str, n: int = 5) -> str:
    matches = difflib.get_close_matches(want, candidates, n=n, cutoff=0.5)
    if not matches:
        return f"  no close {label} matches found"
    bullet = "\n".join(f"    - {m}" for m in matches)
    return f"  did you mean one of:\n{bullet}"


def _suggest_field(g: OdooGraph, target: str) -> str:
    """When a 'model.field' lookup fails, try to suggest a fix.

    Two failure modes:
      1) Wrong model split (e.g. dropped a dot): suggest models close to the
         best-guess model substring.
      2) Right model, wrong field name: suggest fields on that model.
    """
    parts = target.split(".")
    # Try each split position; for each, score "model exists" + "fields close"
    best_model: Optional[str] = None
    for i in range(len(parts) - 1, 0, -1):
        m = ".".join(parts[:i])
        if g.node(g.model_id(m)) is not None:
            best_model = m
            break
    out = []
    if best_model:
        wanted_field = target[len(best_model) + 1:]
        field_names = [
            n["name"]
            for n in g.nodes_of_kind("Field") if n["model"] == best_model
        ]
        out.append(f"  recognised model: {best_model}")
        out.append(f"  looking for field: {wanted_field!r}")
        out.append(_suggest("field", field_names, wanted_field))
    else:
        # No prefix matched any model. Suggest models close to the longest prefix.
        candidates = [n["name"] for n in g.nodes_of_kind("Model")]
        guess = ".".join(parts[:-1]) if len(parts) > 1 else target
        out.append(f"  no model matches a prefix of {target!r}")
        out.append(_suggest("model", candidates, guess))
    return "\n".join(out)


# ---------- subcommands ----------------------------------------------------

def cmd_dump(args: argparse.Namespace) -> int:
    # Build CLI values first, then fold in conf values so explicit flags win.
    cli_vals = ConfigValues(
        db_host=args.db_host,
        db_port=args.db_port,
        db_user=args.db_user,
        db_password=args.db_password,
        db_name=args.database,
        addons_path=list(args.addons_path or []),
    )
    conf_vals = ConfigValues()
    if args.config:
        try:
            conf_vals = load_config(args.config)
        except FileNotFoundError as exc:
            log.error("%s", exc)
            return 1
        log.info("loaded config: %s", conf_vals.source_path)
        log.debug(
            "config values: db_host=%s db_port=%s db_user=%s db_name=%s "
            "addons_path=%s",
            conf_vals.db_host, conf_vals.db_port, conf_vals.db_user,
            conf_vals.db_name, conf_vals.addons_path,
        )

    effective = merge(cli_vals, conf_vals)
    database = effective.db_name
    if not database:
        log.error(
            "database name required: pass -d or set db_name in the config file",
        )
        return 2
    log.debug(
        "effective: db=%s host=%s port=%s user=%s addons=%d dirs",
        effective.db_name, effective.db_host, effective.db_port,
        effective.db_user, len(effective.addons_path),
    )

    try:
        result = dump_registry(
            database=database,
            odoo_path=args.odoo_path,
            addons_path=effective.addons_path or None,
            db_host=effective.db_host or "127.0.0.1",
            db_port=effective.db_port or 5432,
            db_user=effective.db_user or "odoo",
            db_password=effective.db_password,
            config_file=args.config,
            out_dir=args.out_dir,
        )
    except DumpError as exc:
        log.error("dump failed: %s", exc)
        return 1
    emit(result, kind="dump", fmt=args.format)
    return 0


def cmd_field(args: argparse.Namespace) -> int:
    g = _load(args)
    model, name = _split_model_field(g, args.target)
    if not model or not name:
        log.error("field target must be 'model.field' (got %r)", args.target)
        return 2
    log.debug("field query: model=%s name=%s", model, name)
    try:
        payload = g.field_lineage(model, name)
    except KeyError as exc:
        log.error("%s", exc)
        log.info("\n%s", _suggest_field(g, args.target))
        return 1
    log.info(
        "field %s.%s: %d upstream / %d downstream",
        model, name, len(payload["upstream"]), len(payload["downstream"]),
    )
    emit(payload, kind="field", fmt=args.format)
    return 0


def cmd_model(args: argparse.Namespace) -> int:
    g = _load(args)
    try:
        payload = g.model_summary(args.target)
    except KeyError as exc:
        log.error("%s", exc)
        candidates = [n["name"] for n in g.nodes_of_kind("Model")]
        log.info("\n%s", _suggest("model", candidates, args.target))
        return 1
    log.info(
        "model %s: extended by %d module(s), %d field group(s)",
        args.target, len(payload["extended_by_modules"]),
        len(payload["fields_by_module"]),
    )
    emit(payload, kind="model", fmt=args.format)
    return 0


def cmd_module(args: argparse.Namespace) -> int:
    g = _load(args)
    try:
        payload = g.module_summary(args.target)
    except KeyError as exc:
        log.error("%s", exc)
        candidates = [n["name"] for n in g.nodes_of_kind("Module")]
        log.info("\n%s", _suggest("module", candidates, args.target))
        return 1
    log.info(
        "module %s: %d original models, %d extended models",
        args.target, len(payload["original_models"]),
        len(payload["extended_models"]),
    )
    emit(payload, kind="module", fmt=args.format)
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    g = _load(args)
    model, name = _split_model_field(g, args.target)
    if not model or not name:
        log.error("impact target must be 'model.field' (got %r)", args.target)
        return 2
    try:
        hits = g.impact(model, name, max_depth=args.max_depth)
    except KeyError as exc:
        log.error("%s", exc)
        log.info("\n%s", _suggest_field(g, args.target))
        return 1
    log.info(
        "impact %s.%s (depth<=%d): %d affected fields",
        model, name, args.max_depth, len(hits),
    )
    emit(
        {"target": {"model": model, "name": name},
         "max_depth": args.max_depth, "impacted": hits},
        kind="impact", fmt=args.format,
    )
    return 0


def cmd_overrides(args: argparse.Namespace) -> int:
    g = _load(args)
    # Methods follow the same model.method shape; reuse the splitter (it works
    # the same way — first prefix that matches a real model wins).
    model, method = _split_model_field(g, args.target)
    if not model or not method:
        log.error("overrides target must be 'model.method' (got %r)", args.target)
        return 2
    try:
        payload = g.overrides_of(model, method)
    except KeyError as exc:
        log.error("%s", exc)
        # Suggest method names defined on this model, if we identified one.
        if g.node(g.model_id(model)) is not None:
            method_names = sorted({
                n["name"] for n in g.nodes_of_kind("Method")
                if n["model"] == model
            })
            log.info("\n%s", _suggest("method", method_names, method))
        return 1
    log.info(
        "overrides %s.%s: depth=%d",
        model, method, payload.get("override_depth", 0),
    )
    emit(payload, kind="overrides", fmt=args.format)
    return 0


def cmd_path(args: argparse.Namespace) -> int:
    g = _load(args)

    # Start may be "model" or "model.field".
    if g.node(g.model_id(args.start)) is not None:
        start_nid = g.model_id(args.start)
    else:
        start_model, start_name = _split_model_field(g, args.start)
        if start_model and start_name:
            start_nid = g.field_id(start_model, start_name)
            if g.node(start_nid) is None:
                if g.node(g.model_id(start_model)) is not None:
                    log.error("Field not found: %s.%s", start_model, start_name)
                    log.info("\n%s", _suggest_field(g, args.start))
                    return 1
                log.error("Model not found: %s", args.start)
                candidates = [n["name"] for n in g.nodes_of_kind("Model")]
                log.info("\n%s", _suggest("model", candidates, args.start))
                return 1
        else:
            log.error("Model not found: %s", args.start)
            candidates = [n["name"] for n in g.nodes_of_kind("Model")]
            log.info("\n%s", _suggest("model", candidates, args.start))
            return 1

    target_model, target_name = _split_model_field(g, args.target)
    if not target_model or not target_name:
        log.error("path target must be 'model.field' (got %r)", args.target)
        return 2
    target_nid = g.field_id(target_model, target_name)
    if g.node(target_nid) is None:
        log.error("Field not found: %s.%s", target_model, target_name)
        log.info("\n%s", _suggest_field(g, args.target))
        return 1

    allow_kinds = None
    if args.allow_kinds:
        allow_kinds = [k.strip() for k in args.allow_kinds.split(",") if k.strip()]
    payload = g.find_path(
        start_nid,
        target_nid,
        max_depth=args.max_depth,
        max_paths=args.max_paths,
        allow_kinds=allow_kinds,
    )
    log.info(
        "path %s -> %s: %d path(s) (depth<=%d)",
        args.start, args.target, len(payload["paths"]), args.max_depth,
    )
    emit(payload, kind="path", fmt=args.format)
    return 0


# ---------- parser ---------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="odoo-graph")
    p.add_argument("--version", action="version", version=f"odoo-graph {__version__}")
    p.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase log verbosity (-v=DEBUG). Overrides --log-level.",
    )
    p.add_argument(
        "--log-level", default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set log level (default: INFO; or $ODOO_GRAPH_LOG).",
    )
    p.add_argument(
        "-q", "--quiet", action="store_true",
        help="Only print errors. Equivalent to --log-level ERROR.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # dump
    pd = sub.add_parser("dump", help="Run Odoo and dump the registry graph.")
    pd.add_argument(
        "-c", "--config", default=os.environ.get("ODOO_RC"),
        help="Path to an Odoo config file (odoo.conf / ~/.odoorc). "
             "Provides defaults for db_host/db_port/db_user/db_password/"
             "addons_path. Explicit CLI flags override conf values. "
             "The file is also passed through to `odoo-bin -c` so Odoo "
             "reads its other options (data_dir, log settings, ...).",
    )
    pd.add_argument("-d", "--database", default=None,
                    help="Odoo database name (or read from conf 'db_name')")
    pd.add_argument("--odoo-path", default=os.environ.get("ODOO_PATH", "./odoo-17.0"),
                    help="Path to Odoo source tree (contains odoo-bin). "
                         "Default: $ODOO_PATH or ./odoo-17.0")
    pd.add_argument("--addons-path", action="append", default=[],
                    help="Extra addons dir (repeatable). Merged with "
                         "addons_path from -c.")
    pd.add_argument("--db-host", default=None,
                    help="Postgres host (default from conf or 127.0.0.1)")
    pd.add_argument("--db-port", type=int, default=None,
                    help="Postgres port (default from conf or 5432)")
    pd.add_argument("--db-user", "-r", default=None,
                    help="Postgres user (default from conf or 'odoo')")
    pd.add_argument("--db-password", "-w", default=os.environ.get("PGPASSWORD"),
                    help="Postgres password (default from conf or $PGPASSWORD)")
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

    # path
    pp = sub.add_parser(
        "path",
        help="Find directed paths from a model/field start to a target field.",
    )
    pp.add_argument(
        "start",
        help="Start from model or model.field, e.g. ifs.gar.partner.supplier.merchant",
    )
    pp.add_argument(
        "target",
        help="Target field model.field, e.g. ifs.gar.sub.loan.account.t18_contract_info_id",
    )
    pp.add_argument("--max-depth", type=int, default=6)
    pp.add_argument("--max-paths", type=int, default=3)
    pp.add_argument(
        "--allow-kinds",
        default=None,
        help="Comma-separated edge kinds for debugging, e.g. MODEL_HAS_FIELD,FIELD_DEPENDS_ON_FIELD",
    )
    _add_common_query_args(pp)
    pp.set_defaults(func=cmd_path)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # CLI flag precedence: --quiet > -v > --log-level > $ODOO_GRAPH_LOG > INFO
    level: Optional[str] = None
    if getattr(args, "quiet", False):
        level = "ERROR"
    elif getattr(args, "log_level", None):
        level = args.log_level
    setup_logging(level=level, verbosity=getattr(args, "verbose", 0))
    log.debug("argv=%r", argv if argv is not None else sys.argv[1:])
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
