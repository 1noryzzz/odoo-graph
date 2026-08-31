"""`odoo-graph` CLI entry point."""
from __future__ import annotations

import argparse
import difflib
import os
import shlex
import sys
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

from . import __version__
from .config import ConfigValues, load_config, merge
from .dump import (
    DumpError,
    OdooPathResolutionError,
    _default_cache_dir,
    dump as dump_registry,
    resolve_odoo_path,
)
from .formatters import FORMATS, emit
from .graph import OdooGraph, load_graph
from .logging import get_logger, setup_logging
from .telemetry.report import build_report, render_report
from .telemetry.runtime import (
    TRACKED_COMMANDS,
    InvocationRecorder,
    dump_result_size,
    field_meta,
    model_meta,
    telemetry_enabled,
)
from .telemetry.store import init_db

log = get_logger(__name__)
MAX_BATCH_TARGETS = 50


def _add_no_telemetry_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--no-telemetry", action="store_true", default=argparse.SUPPRESS,
        help="Disable local telemetry for this invocation.",
    )


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
    _add_no_telemetry_arg(p)


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
    out_dir = _resolve_out_dir(args)
    t0 = time.monotonic()
    graph = load_graph(out_dir)
    rec = _telemetry(args)
    if rec:
        rec.record_load(time.monotonic() - t0, graph, out_dir)
    return graph


def _telemetry(args: argparse.Namespace) -> InvocationRecorder | None:
    return getattr(args, "_telemetry", None)


def _query_started() -> float:
    return time.monotonic()


def _query_done(args: argparse.Namespace, started: float) -> None:
    rec = _telemetry(args)
    if rec:
        rec.add_query_seconds(time.monotonic() - started)


def _telemetry_error(
    args: argparse.Namespace,
    result_status: str,
    error_category: str,
) -> None:
    rec = _telemetry(args)
    if rec:
        rec.set_error(result_status, error_category)


def _emit_payload(
    args: argparse.Namespace,
    payload: dict[str, Any],
    *,
    kind: str,
    fmt: str,
    summary: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    size: int | None = None,
    empty: bool = False,
) -> None:
    rec = _telemetry(args)
    if rec:
        rec.set_result(summary=summary, meta=meta, size=size, empty=empty)
    t0 = time.monotonic()
    try:
        emit(payload, kind=kind, fmt=fmt)
    finally:
        if rec:
            rec.add_output_seconds(time.monotonic() - t0)


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


def _field_suggestions(g: OdooGraph, target: str, n: int = 3) -> list[str]:
    model, name = _split_model_field(g, target)
    if model and g.node(g.model_id(model)) is not None:
        field_names = [
            node["name"]
            for node in g.nodes_of_kind("Field")
            if node["model"] == model
        ]
        return [
            f"{model}.{match}"
            for match in difflib.get_close_matches(
                name,
                field_names,
                n=n,
                cutoff=0.5,
            )
        ]
    model_names = [node["name"] for node in g.nodes_of_kind("Model")]
    return difflib.get_close_matches(model, model_names, n=n, cutoff=0.5)


def _method_suggestions(
    g: OdooGraph,
    model: str,
    method: str,
    n: int = 3,
) -> list[str]:
    if g.node(g.model_id(model)) is None:
        model_names = [node["name"] for node in g.nodes_of_kind("Model")]
        return difflib.get_close_matches(model, model_names, n=n, cutoff=0.5)
    method_names = sorted({
        node["name"]
        for node in g.nodes_of_kind("Method")
        if node["model"] == model
    })
    return [
        f"{model}.{match}"
        for match in difflib.get_close_matches(
            method,
            method_names,
            n=n,
            cutoff=0.5,
        )
    ]


def _batch_result(found: int, requested: int) -> str:
    if found == requested:
        return "success"
    if found:
        return "partial"
    return "not_found"


def _validate_batch_size(
    args: argparse.Namespace,
    targets: list[str],
    *,
    kind: str,
) -> bool:
    rec = _telemetry(args)
    if rec:
        rec.set_target(kind=kind, raw=",".join(targets))
    if len(targets) <= MAX_BATCH_TARGETS:
        return True
    log.error(
        "%s accepts at most %d targets (got %d)",
        args.cmd,
        MAX_BATCH_TARGETS,
        len(targets),
    )
    if rec:
        rec.set_result(
            summary={
                "requested": len(targets),
                "limit": MAX_BATCH_TARGETS,
            },
            empty=True,
        )
    _telemetry_error(args, "usage_error", "usage_error")
    return False


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
            _telemetry_error(args, "usage_error", "usage_error")
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
        _telemetry_error(args, "usage_error", "usage_error")
        return 2
    log.debug(
        "effective: db=%s host=%s port=%s user=%s addons=%d dirs",
        effective.db_name, effective.db_host, effective.db_port,
        effective.db_user, len(effective.addons_path),
    )

    env_odoo_path = os.environ.get("ODOO_PATH")
    requested_odoo_path = (
        args.odoo_path if args.odoo_path is not None else env_odoo_path
    )
    path_source = (
        "cli"
        if args.odoo_path is not None
        else "env"
        if env_odoo_path is not None
        else "auto"
    )
    rec = _telemetry(args)
    if rec:
        rec.add_extra(odoo_path_source=path_source)

    try:
        t0 = _query_started()
        resolution = resolve_odoo_path(
            requested_odoo_path,
            source=path_source,
        )
        if rec:
            rec.add_extra(odoo_path_resolved=resolution.path)
        if resolution.source == "auto":
            log.debug(
                "resolved odoo_path from cwd candidate %s: %s",
                resolution.candidate,
                resolution.path,
            )
        result = dump_registry(
            database=database,
            odoo_path=resolution.path,
            addons_path=effective.addons_path or None,
            db_host=effective.db_host or "127.0.0.1",
            db_port=effective.db_port or 5432,
            db_user=effective.db_user or "odoo",
            db_password=effective.db_password,
            config_file=args.config,
            out_dir=args.out_dir,
        )
        _query_done(args, t0)
    except OdooPathResolutionError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        if exc.found_candidate:
            command = ["odoo-graph", "dump"]
            if args.config:
                command.extend(["-c", args.config])
            command.extend(["-d", database, "--odoo-path", exc.found_candidate])
            log.error(
                "\nSuggested command:\n  %s",
                " ".join(shlex.quote(part) for part in command),
            )
        if rec:
            rec.add_extra(odoo_path_failure_reason=exc.reason)
        _telemetry_error(args, "dump_error", "dump_error")
        return 1
    except DumpError as exc:
        _query_done(args, t0)
        log.error("dump failed: %s", exc)
        log.error(
            "re-run with -v for the Odoo stderr tail; verify -c/-d, --odoo-path, "
            "addons paths, and PostgreSQL connection settings before retrying"
        )
        _telemetry_error(args, "dump_error", "dump_error")
        return 1
    summary = result.get("summary") or {}
    result_summary = {
        "models_count": summary.get("models"),
        "fields_count": summary.get("fields"),
        "resolved_count": (result.get("resolve") or {}).get("resolved"),
        "unresolved_count": (result.get("resolve") or {}).get("unresolved"),
    }
    _emit_payload(
        args,
        result,
        kind="dump",
        fmt=args.format,
        summary=result_summary,
        size=dump_result_size(summary),
        empty=dump_result_size(summary) == 0,
    )
    return 0


def _cmd_field_single(
    args: argparse.Namespace,
    g: OdooGraph,
    target: str,
) -> int:
    model, name = _split_model_field(g, target)
    rec = _telemetry(args)
    if rec:
        rec.set_target(kind="field", raw=target, model=model, field=name)
    if not model or not name:
        log.error("field target must be 'model.field' (got %r)", target)
        _telemetry_error(args, "usage_error", "usage_error")
        return 2
    log.debug("field query: model=%s name=%s", model, name)
    t0 = _query_started()
    try:
        payload = g.field_lineage(model, name)
    except KeyError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        log.info("\n%s", _suggest_field(g, target))
        _telemetry_error(args, "not_found", "not_found")
        return 1
    _query_done(args, t0)
    log.info(
        "field %s.%s: %d upstream / %d downstream",
        model, name, len(payload["upstream"]), len(payload["downstream"]),
    )
    upstream_count = len(payload["upstream"])
    downstream_count = len(payload["downstream"])
    _emit_payload(
        args,
        payload,
        kind="field",
        fmt=args.format,
        summary={
            "upstream_count": upstream_count,
            "downstream_count": downstream_count,
            "primary_count_name": "downstream_count",
        },
        meta=field_meta(payload["field"], upstream_count=upstream_count),
        size=upstream_count + downstream_count,
        empty=upstream_count + downstream_count == 0,
    )
    return 0


def cmd_field(args: argparse.Namespace) -> int:
    targets = args.targets
    if not _validate_batch_size(args, targets, kind="field"):
        return 2
    g = _load(args)
    if len(targets) == 1:
        return _cmd_field_single(args, g, targets[0])

    t0 = _query_started()
    items: list[dict[str, Any]] = []
    found = 0
    for target in targets:
        model, name = _split_model_field(g, target)
        if not model or not name:
            items.append({
                "target": target,
                "status": "not_found",
                "suggestions": _field_suggestions(g, target),
            })
            continue
        try:
            field_payload = g.field_lineage(model, name)
        except KeyError:
            items.append({
                "target": target,
                "status": "not_found",
                "suggestions": _field_suggestions(g, target),
            })
            continue
        items.append({
            "target": target,
            "status": "found",
            **field_payload,
        })
        found += 1
    _query_done(args, t0)
    missing = len(targets) - found
    result = _batch_result(found, len(targets))
    payload = {
        "kind": "field_batch",
        "targets": items,
        "summary": {
            "requested": len(targets),
            "found": found,
            "missing": missing,
        },
    }
    log.info(
        "field batch: %d requested, %d found, %d missing",
        len(targets),
        found,
        missing,
    )
    _emit_payload(
        args,
        payload,
        kind="field_batch",
        fmt=args.format,
        summary={
            "result": result,
            "requested": len(targets),
            "found": found,
            "missing": missing,
        },
        size=found,
        empty=found == 0,
    )
    if result == "not_found":
        _telemetry_error(args, "not_found", "not_found")
        return 1
    return 0


def cmd_model(args: argparse.Namespace) -> int:
    g = _load(args)
    rec = _telemetry(args)
    if rec:
        rec.set_target(kind="model", raw=args.target, model=args.target)
    t0 = _query_started()
    try:
        payload = g.model_summary(args.target)
    except KeyError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        candidates = [n["name"] for n in g.nodes_of_kind("Model")]
        log.info("\n%s", _suggest("model", candidates, args.target))
        _telemetry_error(args, "not_found", "not_found")
        return 1
    _query_done(args, t0)
    log.info(
        "model %s: extended by %d module(s), %d field group(s)",
        args.target, len(payload["extended_by_modules"]),
        len(payload["fields_by_module"]),
    )
    fields_count = sum(len(v) for v in payload["fields_by_module"].values())
    _emit_payload(
        args,
        payload,
        kind="model",
        fmt=args.format,
        summary={
            "extended_by_modules_count": len(payload["extended_by_modules"]),
            "fields_by_module_count": len(payload["fields_by_module"]),
            "delegation_chain_count": len(payload.get("delegation_chain") or []),
        },
        meta=model_meta(payload["model"]),
        size=fields_count,
        empty=fields_count == 0,
    )
    return 0


def cmd_module(args: argparse.Namespace) -> int:
    g = _load(args)
    rec = _telemetry(args)
    if rec:
        rec.set_target(kind="module", raw=args.target, module=args.target)
    t0 = _query_started()
    try:
        payload = g.module_summary(args.target)
    except KeyError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        candidates = [n["name"] for n in g.nodes_of_kind("Module")]
        log.info("\n%s", _suggest("module", candidates, args.target))
        _telemetry_error(args, "not_found", "not_found")
        return 1
    _query_done(args, t0)
    log.info(
        "module %s: %d original models, %d extended models",
        args.target, len(payload["original_models"]),
        len(payload["extended_models"]),
    )
    size = (
        len(payload["original_models"])
        + len(payload["extended_models"])
        + len(payload["original_fields"])
        + len(payload["extended_fields"])
    )
    _emit_payload(
        args,
        payload,
        kind="module",
        fmt=args.format,
        summary={
            "original_models_count": len(payload["original_models"]),
            "extended_models_count": len(payload["extended_models"]),
            "original_fields_count": len(payload["original_fields"]),
            "extended_fields_count": len(payload["extended_fields"]),
        },
        size=size,
        empty=size == 0,
    )
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    g = _load(args)
    model, name = _split_model_field(g, args.target)
    rec = _telemetry(args)
    if rec:
        rec.set_target(kind="field", raw=args.target, model=model, field=name)
    if not model or not name:
        log.error("impact target must be 'model.field' (got %r)", args.target)
        _telemetry_error(args, "usage_error", "usage_error")
        return 2
    t0 = _query_started()
    try:
        hits = g.impact(model, name, max_depth=args.max_depth)
    except KeyError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        log.info("\n%s", _suggest_field(g, args.target))
        _telemetry_error(args, "not_found", "not_found")
        return 1
    _query_done(args, t0)
    log.info(
        "impact %s.%s (depth<=%d): %d affected fields",
        model, name, args.max_depth, len(hits),
    )
    payload = {
        "target": {"model": model, "name": name},
        "max_depth": args.max_depth,
        "impacted": hits,
    }
    _emit_payload(
        args,
        payload,
        kind="impact", fmt=args.format,
        summary={"impacted_count": len(hits)},
        size=len(hits),
        empty=len(hits) == 0,
    )
    return 0


def cmd_path(args: argparse.Namespace) -> int:
    g = _load(args)
    start_model: Optional[str] = None
    start_field: Optional[str] = None

    if g.node(g.model_id(args.start)) is not None:
        start_model = args.start
    else:
        sm, sf = _split_model_field(g, args.start)
        if sm and sf:
            start_model, start_field = sm, sf
        else:
            log.error("path start must be 'model' or 'model.field' (got %r)", args.start)
            _telemetry_error(args, "usage_error", "usage_error")
            return 2

    target_model, target_field = _split_model_field(g, args.target)
    if not target_model or not target_field:
        log.error("path target must be 'model.field' (got %r)", args.target)
        _telemetry_error(args, "usage_error", "usage_error")
        return 2

    rec = _telemetry(args)
    if rec:
        rec.set_start(
            kind="field" if start_field else "model",
            raw=args.start,
            model=start_model,
            field=start_field,
        )
        rec.set_target(
            kind="field",
            raw=args.target,
            model=target_model,
            field=target_field,
        )

    allow_kinds = None
    if args.allow_kinds:
        allow_kinds = [k.strip() for k in args.allow_kinds.split(",") if k.strip()]

    t0 = _query_started()
    try:
        payload = g.find_path(
            start_model=start_model,
            start_field=start_field,
            target_model=target_model,
            target_field=target_field,
            max_depth=args.max_depth,
            max_paths=args.max_paths,
            edge_kinds=allow_kinds,
        )
    except KeyError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        log.info("\nstart suggestion:\n%s", _suggest_field(g, args.start))
        log.info("\ntarget suggestion:\n%s", _suggest_field(g, args.target))
        _telemetry_error(args, "not_found", "not_found")
        return 1
    except ValueError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        _telemetry_error(args, "usage_error", "usage_error")
        return 2
    _query_done(args, t0)

    log.info(
        "path %s -> %s.%s: %d path(s)",
        args.start, target_model, target_field, payload["summary"]["found_paths"],
    )
    found_paths = payload["summary"]["found_paths"]
    _emit_payload(
        args,
        payload,
        kind="path",
        fmt=args.format,
        summary={
            "found_paths": found_paths,
            "truncated": payload.get("truncated"),
        },
        size=found_paths,
        empty=found_paths == 0,
    )
    return 0


def _cmd_overrides_single(
    args: argparse.Namespace,
    g: OdooGraph,
    target: str,
) -> int:
    # Methods follow the same model.method shape; reuse the splitter (it works
    # the same way — first prefix that matches a real model wins).
    model, method = _split_model_field(g, target)
    rec = _telemetry(args)
    if rec:
        rec.set_target(kind="method", raw=target, model=model, method=method)
    if not model or not method:
        log.error("overrides target must be 'model.method' (got %r)", target)
        _telemetry_error(args, "usage_error", "usage_error")
        return 2
    t0 = _query_started()
    try:
        payload = g.overrides_of(model, method)
    except KeyError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        # Suggest method names defined on this model, if we identified one.
        if g.node(g.model_id(model)) is not None:
            method_names = sorted({
                n["name"] for n in g.nodes_of_kind("Method")
                if n["model"] == model
            })
            log.info("\n%s", _suggest("method", method_names, method))
        _telemetry_error(args, "not_found", "not_found")
        return 1
    _query_done(args, t0)
    log.info(
        "overrides %s.%s: depth=%d",
        model, method, payload.get("override_depth", 0),
    )
    class_count = len(payload.get("defined_in_classes") or [])
    _emit_payload(
        args,
        payload,
        kind="overrides",
        fmt=args.format,
        summary={
            "override_depth": payload.get("override_depth"),
            "defined_in_classes_count": class_count,
        },
        size=class_count,
        empty=class_count == 0,
    )
    return 0


def cmd_overrides(args: argparse.Namespace) -> int:
    targets = args.targets
    if not _validate_batch_size(args, targets, kind="method"):
        return 2
    g = _load(args)
    if len(targets) == 1:
        return _cmd_overrides_single(args, g, targets[0])

    t0 = _query_started()
    items: list[dict[str, Any]] = []
    found = 0
    for target in targets:
        model, method = _split_model_field(g, target)
        if not model or not method:
            items.append({
                "target": target,
                "status": "not_found",
                "suggestions": _method_suggestions(g, model, method),
            })
            continue
        try:
            override_payload = g.overrides_of(model, method)
        except KeyError:
            items.append({
                "target": target,
                "status": "not_found",
                "suggestions": _method_suggestions(g, model, method),
            })
            continue
        items.append({
            "target": target,
            "status": "found",
            **override_payload,
        })
        found += 1
    _query_done(args, t0)
    missing = len(targets) - found
    result = _batch_result(found, len(targets))
    payload = {
        "kind": "overrides_batch",
        "targets": items,
        "summary": {
            "requested": len(targets),
            "found": found,
            "missing": missing,
        },
    }
    log.info(
        "override batch: %d requested, %d found, %d missing",
        len(targets),
        found,
        missing,
    )
    _emit_payload(
        args,
        payload,
        kind="overrides_batch",
        fmt=args.format,
        summary={
            "result": result,
            "requested": len(targets),
            "found": found,
            "missing": missing,
        },
        size=found,
        empty=found == 0,
    )
    if result == "not_found":
        _telemetry_error(args, "not_found", "not_found")
        return 1
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    g = _load(args)
    rec = _telemetry(args)
    if rec:
        rec.set_target(kind="model", raw=",".join(args.models), model=args.models[0])
    t0 = _query_started()
    try:
        payload = g.context_summary(args.models)
    except ValueError as exc:
        _query_done(args, t0)
        log.error("%s", exc)
        _telemetry_error(args, "usage_error", "usage_error")
        return 2
    _query_done(args, t0)
    resolved_count = len(payload.get("selected_models") or [])
    missing_count = len(payload.get("missing_models") or [])
    log.info(
        "context %s: %d resolved, %d missing, %d relationship(s), %d suggestion(s)",
        ",".join(args.models),
        resolved_count,
        missing_count,
        len(payload.get("relationships") or []),
        len(payload.get("suggested_context_models") or []),
    )
    result = payload["result"]
    size = (
        resolved_count
        + len(payload.get("relationships") or [])
        + len(payload.get("suggested_context_models") or [])
    )
    _emit_payload(
        args,
        payload,
        kind="context",
        fmt=args.format,
        summary={
            "result": result,
            "requested": len(payload.get("requested_models") or []),
            "resolved": resolved_count,
            "missing": missing_count,
            "mode": payload.get("mode"),
            "relationships_count": len(payload.get("relationships") or []),
            "suggested_context_models_count": len(payload.get("suggested_context_models") or []),
        },
        meta={"models": payload.get("requested_models")},
        size=size,
        empty=result == "not_found",
    )
    if result == "not_found":
        _telemetry_error(args, "not_found", "not_found")
        return 1
    return 0


def cmd_telemetry_init(args: argparse.Namespace) -> int:
    path = init_db(args.db)
    print(path)
    return 0


def cmd_telemetry_report(args: argparse.Namespace) -> int:
    report = build_report(args.db, gap_seconds=args.gap_seconds)
    print(render_report(report, fmt=args.format))
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
    p.add_argument(
        "--no-telemetry", action="store_true",
        help="Disable local telemetry for this invocation.",
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
    pd.add_argument("--odoo-path", default=None,
                    help="Path to Odoo source tree (contains odoo-bin). "
                         "Default: $ODOO_PATH, then deterministic cwd probing.")
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
    _add_no_telemetry_arg(pd)
    pd.set_defaults(func=cmd_dump)

    # field
    pf = sub.add_parser("field", help="Lineage (upstream/downstream) for a field.")
    pf.add_argument(
        "targets",
        nargs="+",
        help="One or more model.field targets (maximum 50).",
    )
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

    # context
    pc = sub.add_parser("context", help="Seed-first model context and related model suggestions.")
    pc.add_argument("models", nargs="+", help="One seed model or an explicit model group.")
    _add_common_query_args(pc)
    pc.set_defaults(func=cmd_context)

    # impact
    pi = sub.add_parser("impact", help="Downstream recompute impact of a field.")
    pi.add_argument("target", help="model.field")
    pi.add_argument("--max-depth", type=int, default=3)
    _add_common_query_args(pi)
    pi.set_defaults(func=cmd_impact)

    # path
    pp = sub.add_parser("path", help="Find path(s) from a start model/field to a target field.")
    pp.add_argument("start", help="Start point: model or model.field")
    pp.add_argument("target", help="Target field: model.field")
    pp.add_argument("--max-depth", type=int, default=6)
    pp.add_argument("--max-paths", type=int, default=3)
    pp.add_argument(
        "--allow-kinds",
        default=None,
        help="Comma-separated edge kinds whitelist.",
    )
    _add_common_query_args(pp)
    pp.set_defaults(func=cmd_path)

    # overrides
    po = sub.add_parser("overrides", help="Override chain of a method.")
    po.add_argument(
        "targets",
        nargs="+",
        help="One or more model.method targets (maximum 50).",
    )
    _add_common_query_args(po)
    po.set_defaults(func=cmd_overrides)

    # telemetry
    pt = sub.add_parser("telemetry", help="Manage and analyze local CLI telemetry.")
    tsub = pt.add_subparsers(dest="telemetry_cmd", required=True)

    pti = tsub.add_parser("init", help="Initialize the local telemetry SQLite DB.")
    pti.add_argument(
        "--db", default=None,
        help="Telemetry SQLite path. Default: ~/.cache/odoo-graph/telemetry.sqlite3 "
             "or $ODOO_GRAPH_TELEMETRY_DB.",
    )
    pti.set_defaults(func=cmd_telemetry_init)

    ptr = tsub.add_parser("report", help="Analyze collected telemetry.")
    ptr.add_argument(
        "--db", default=None,
        help="Telemetry SQLite path. Default: ~/.cache/odoo-graph/telemetry.sqlite3 "
             "or $ODOO_GRAPH_TELEMETRY_DB.",
    )
    ptr.add_argument("--gap-seconds", type=int, default=60)
    ptr.add_argument("--format", "-f", choices=("human", "json"), default="human")
    ptr.set_defaults(func=cmd_telemetry_report)

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
    rec: InvocationRecorder | None = None
    if args.cmd in TRACKED_COMMANDS and telemetry_enabled(args):
        rec = InvocationRecorder.from_args(args, argv)
        setattr(args, "_telemetry", rec)
    try:
        rc = int(args.func(args) or 0)
    except SystemExit as exc:
        if rec:
            code = exc.code if isinstance(exc.code, int) else 1
            rec.finish(code)
        raise
    except FileNotFoundError as exc:
        log.error("%s", exc)
        if rec:
            rec.set_error("not_found", "missing_cache")
            rec.finish(1, exc)
        return 1
    except Exception as exc:
        if rec:
            rec.finish(1, exc)
        raise
    if rec:
        rec.finish(rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
