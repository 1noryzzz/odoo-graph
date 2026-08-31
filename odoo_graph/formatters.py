"""Output formatters.

`human` prints a compact text tree. `json` emits a single JSON blob to stdout.
Graphviz output is intentionally not exposed as a CLI format until it is
implemented.
"""
from __future__ import annotations

import json as _json
import sys
from typing import Any, Dict


FORMATS = ("human", "json")


def render(payload: Dict[str, Any], kind: str, fmt: str) -> str:
    if fmt == "json":
        return _json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if fmt == "graphviz":
        raise NotImplementedError(
            "graphviz output is not implemented yet. "
            "Phase 1 focuses on the human formatter; graphviz will plug into "
            "this same dispatch (see formatters.py)."
        )
    return _render_human(payload, kind)


def _render_human(payload: Dict[str, Any], kind: str) -> str:
    if kind == "field":
        return _h_field(payload)
    if kind == "field_batch":
        return _h_field_batch(payload)
    if kind == "model":
        return _h_model(payload)
    if kind == "module":
        return _h_module(payload)
    if kind == "impact":
        return _h_impact(payload)
    if kind == "path":
        return _h_path(payload)
    if kind == "overrides":
        return _h_overrides(payload)
    if kind == "overrides_batch":
        return _h_overrides_batch(payload)
    if kind == "context":
        return _h_context(payload)
    if kind == "dump":
        return _h_dump(payload)
    return _json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _box(title: str) -> str:
    bar = "=" * max(40, len(title) + 4)
    return f"{bar}\n  {title}\n{bar}"


def _h_field(p: Dict[str, Any]) -> str:
    fd = p["field"]
    analysis = p.get("analysis") or {}
    lines = [_box(f"Field  {fd['model']}.{fd['name']}  [{fd['type']}]")]
    lines.append(f"  origin-module : {fd.get('module')}")
    lines.append(f"  all modules   : {fd.get('modules')}")
    if analysis:
        lines.append(f"  kind          : {analysis.get('kind')}")
        lines.append(f"  declared here : {analysis.get('declared_on_model')}")
        lines.append(f"  storage       : {analysis.get('storage')}")
        if analysis.get("source_field"):
            lines.append(f"  source field  : {str(analysis['source_field']).replace('field::', '')}")
        lines.append(f"  writable      : {analysis.get('writable')} ({analysis.get('writable_reason')})")
    extras = []
    if fd.get("compute"):
        extras.append(f"compute={fd['compute']}")
    if fd.get("related"):
        related = analysis.get("related_path") or fd["related"]
        if isinstance(related, list):
            related_s = ".".join(str(x) for x in related)
        else:
            related_s = str(related)
        extras.append("related=" + related_s)
    if fd.get("inverse"):
        extras.append(f"inverse={fd['inverse']}")
    if fd.get("inherited"):
        extras.append(f"inherited_from={fd.get('inherited_from_model')}")
    if fd.get("store"):
        extras.append("stored")
    lines.append(f"  flags         : {', '.join(extras) if extras else '(plain)'}")
    if fd.get("comodel_name"):
        lines.append(f"  comodel       : {fd['comodel_name']}")
    if analysis.get("delegation_chain"):
        lines.append("")
        lines.append("  delegation chain:")
        for hop in analysis["delegation_chain"]:
            lines.append(
                f"    {hop['from_model']}.{hop['field']}"
                f" --{hop['via_field']} ({hop['source']}, path: {hop['path']})--> "
                f"{hop['source_field']}"
            )
    if analysis.get("shadowing"):
        shadow = analysis["shadowing"]
        lines.append("")
        lines.append(f"  shadowing risk: {shadow.get('risk')} - {shadow.get('reason')}")
        for candidate in shadow.get("candidates") or []:
            lines.append(
                f"    candidate: {candidate['field']} via {candidate['via_path']}"
            )
    lines.append("")
    lines.append(f"  upstream (this field depends on):  {len(p['upstream'])} edge(s)")
    for u in p["upstream"]:
        dst_name = u["dst"].replace("field::", "")
        lines.append(f"    <- {dst_name}   (path: {u['path']})")
    lines.append("")
    lines.append(f"  downstream (these fields depend on it):  {len(p['downstream'])} edge(s)")
    for d in p["downstream"]:
        src_name = d["src"].replace("field::", "")
        lines.append(f"    -> {src_name}   (path: {d['path']})")
    return "\n".join(lines)


def _h_field_batch(p: Dict[str, Any]) -> str:
    lines = [f"Field batch  targets={len(p.get('targets') or [])}"]
    for item in p.get("targets") or []:
        lines.extend(["", item["target"], f"  status: {item['status']}"])
        if item["status"] == "not_found":
            if item.get("suggestions"):
                lines.append("  suggestions:")
                lines.extend(
                    f"    {suggestion}"
                    for suggestion in item["suggestions"]
                )
            continue
        field = item["field"]
        analysis = item.get("analysis") or {}
        lines.append(f"  type: {field.get('type')}")
        lines.append(f"  module: {field.get('module')}")
        lines.append(f"  kind: {analysis.get('kind')}")
        lines.append(f"  storage: {analysis.get('storage')}")
        lines.append(
            f"  writable: {analysis.get('writable')}"
            f" ({analysis.get('writable_reason')})"
        )
        upstream = item.get("upstream") or []
        lines.append(f"  upstream: {len(upstream)}")
        for edge in upstream[:5]:
            lines.append(
                f"    <- {edge['dst'].replace('field::', '')}"
                f" (path: {edge.get('path')})"
            )
        if len(upstream) > 5:
            lines.append(f"    ... +{len(upstream) - 5} more")
        downstream = item.get("downstream") or []
        lines.append(f"  downstream: {len(downstream)}")
        for edge in downstream[:5]:
            lines.append(
                f"    -> {edge['src'].replace('field::', '')}"
                f" (path: {edge.get('path')})"
            )
        if len(downstream) > 5:
            lines.append(f"    ... +{len(downstream) - 5} more")
    summary = p["summary"]
    lines.extend([
        "",
        "Summary:",
        f"  requested: {summary['requested']}",
        f"  found: {summary['found']}",
        f"  missing: {summary['missing']}",
    ])
    return "\n".join(lines)


def _h_model(p: Dict[str, Any]) -> str:
    md = p["model"]
    lines = [_box(f"Model  {md['name']}  [{md.get('description')}]")]
    lines.append(f"  original module   : {md.get('original_module')}")
    lines.append(f"  contributing      : {p['extended_by_modules']}")
    lines.append(f"  _inherit          : {md.get('inherit') or []}")
    lines.append(f"  _inherits         : {md.get('inherits') or {}}")
    lines.append(f"  abstract/transient: {md.get('abstract')} / {md.get('transient')}")
    if p.get("delegation_chain"):
        lines.append("")
        lines.append("  Delegation chain:")
        for chain in p["delegation_chain"]:
            rendered = " -> ".join(
                f"{hop['from_model']} --{hop['via_field']} ({hop['source']})--> {hop['to_model']}"
                for hop in chain
            )
            path = chain[-1].get("path")
            lines.append(f"    {rendered}   path={path}")
    lines.append("")
    lines.append("  Fields by module:")
    for mod, flist in sorted(p["fields_by_module"].items(), key=lambda kv: -len(kv[1])):
        lines.append(f"    [{len(flist):>3}]  {mod}")
        for fd in sorted(flist, key=lambda f: f["name"])[:6]:
            marker = []
            if fd.get("compute"): marker.append("C")
            if fd.get("related"): marker.append("R")
            if fd.get("inherited"): marker.append("I")
            flag = ("(" + "".join(marker) + ")") if marker else "   "
            lines.append(f"          - {fd['name']:<30} {fd['type']:<12} {flag}")
        if len(flist) > 6:
            lines.append(f"          ... +{len(flist) - 6} more")
    return "\n".join(lines)


def _h_module(p: Dict[str, Any]) -> str:
    md = p["module"]
    lines = [_box(f"Module  {md['name']}  — {md.get('shortdesc') or ''}")]
    lines.append(f"  depends on         : {[d.replace('module::', '') for d in p['depends']]}")
    lines.append(f"  original models    : {len(p['original_models'])}")
    for mid in sorted(p["original_models"])[:15]:
        lines.append(f"    * {mid.replace('model::', '')}")
    if len(p["original_models"]) > 15:
        lines.append(f"    ... +{len(p['original_models']) - 15}")
    lines.append(f"  extends models     : {len(p['extended_models'])}")
    for em in p["extended_models"][:15]:
        lines.append(f"    + {em['model'].replace('model::', '')}")
    if len(p["extended_models"]) > 15:
        lines.append(f"    ... +{len(p['extended_models']) - 15}")
    lines.append(f"  defines fields     : {len(p['original_fields'])}")
    lines.append(f"  extends fields     : {len(p['extended_fields'])}")
    return "\n".join(lines)


def _h_impact(p: Dict[str, Any]) -> str:
    target = p["target"]
    hits = p["impacted"]
    lines = [_box(f"Impact  {target['model']}.{target['name']}  (max_depth={p['max_depth']})")]
    lines.append(f"  affected fields: {len(hits)}")
    for h in hits[:100]:
        indent = "  " + "  " * (h["depth"] - 1)
        lines.append(f"{indent}(d={h['depth']}) {h['field'].replace('field::', '')}   via '{h['via_path']}'")
    if len(hits) > 100:
        lines.append(f"  ... +{len(hits) - 100} more")
    return "\n".join(lines)


def _h_overrides(p: Dict[str, Any]) -> str:
    md = p
    lines = [_box(f"Overrides  {md['model']}.{md['name']}  (depth={md['override_depth']})")]
    chain = md.get("defined_in_classes", [])
    for i, c in enumerate(chain):
        arrow = "  ┬ " if i == 0 else "  │ "
        lines.append(f"{arrow}[{i}] class={c['class']}  addon={c.get('addon')}  module={c.get('module')}")
    if chain:
        lines.append("  └─ (base)")
    return "\n".join(lines)


def _h_overrides_batch(p: Dict[str, Any]) -> str:
    lines = [f"Override batch  targets={len(p.get('targets') or [])}"]
    for item in p.get("targets") or []:
        lines.extend(["", item["target"], f"  status: {item['status']}"])
        if item["status"] == "not_found":
            if item.get("suggestions"):
                lines.append("  suggestions:")
                lines.extend(
                    f"    {suggestion}"
                    for suggestion in item["suggestions"]
                )
            continue
        lines.append(f"  depth: {item.get('override_depth', 0)}")
        lines.append("  chain:")
        for entry in item.get("defined_in_classes") or []:
            lines.append(
                f"    {entry.get('class')}"
                f"  addon={entry.get('addon')}"
                f"  module={entry.get('module')}"
            )
    summary = p["summary"]
    lines.extend([
        "",
        "Summary:",
        f"  requested: {summary['requested']}",
        f"  found: {summary['found']}",
        f"  missing: {summary['missing']}",
    ])
    return "\n".join(lines)


def _h_path(p: Dict[str, Any]) -> str:
    s = p["summary"]
    start = s["start_model"] if not s.get("start_field") else f"{s['start_model']}.{s['start_field']}"
    target = f"{s['target_model']}.{s['target_field']}"
    lines = [_box(f"Path  {start}  ->  {target}  (max_depth={s['max_depth']})")]
    lines.append(f"  found paths : {s['found_paths']} / max_paths={s['max_paths']}")
    lines.append(f"  truncated   : {p.get('truncated')}")
    lines.append(f"  edge kinds  : {', '.join(s.get('edge_kinds') or [])}")

    for idx, path in enumerate(p.get("paths", []), start=1):
        lines.append("")
        lines.append(f"  [{idx}] depth={path.get('depth')}")
        hops = path.get("hops") or []
        if not hops:
            lines.append("      (start already equals target)")
            continue
        for hop in hops:
            detail = f"kind={hop.get('edge_kind')}"
            if hop.get("path"):
                detail += f", via='{hop.get('path')}'"
            lines.append(
                f"      {hop.get('src', '').replace('field::', '').replace('model::', '')}"
                f" -> {hop.get('dst', '').replace('field::', '').replace('model::', '')}"
                f"  ({detail})"
            )

    return "\n".join(lines)


def _h_context(p: Dict[str, Any]) -> str:
    title_models = ", ".join(p.get("requested_models") or [])
    lines = [_box(f"Context  {title_models}  [{p.get('mode')}]")]
    lines.append(f"  requested models : {p.get('requested_models') or []}")

    lines.append("")
    lines.append("  Resolved models:")
    for item in p.get("models") or []:
        md = item["model"]
        field_count = sum(len(v) for v in item.get("fields_by_module", {}).values())
        lines.append(
            f"    - {md['name']}  module={md.get('original_module')}  "
            f"fields={field_count}  contributing={item.get('extended_by_modules') or []}"
        )
        if md.get("inherit"):
            lines.append(f"      _inherit: {md.get('inherit')}")
        if md.get("inherits"):
            lines.append(f"      _inherits: {md.get('inherits')}")

    if p.get("missing_models"):
        lines.append("")
        lines.append("  Missing models:")
        for item in p["missing_models"]:
            lines.append(f"    - {item['name']}")
            if item.get("suggestions"):
                lines.append("      suggestions:")
                for suggestion in item["suggestions"]:
                    lines.append(f"        - {suggestion}")

    lines.append("")
    lines.append(f"  Relationships: {len(p.get('relationships') or [])}")
    for rel in p.get("relationships") or []:
        via = f" via {rel.get('via_field')}" if rel.get("via_field") else ""
        lines.append(
            f"    - {rel.get('kind')}: {rel.get('from_model')} -> {rel.get('to_model')}"
            f"{via} ({rel.get('source') or rel.get('field_type')})"
        )

    lines.append("")
    lines.append(f"  Relation fields: {len(p.get('relations') or [])}")
    for rel in p.get("relations") or []:
        marker = "selected" if rel.get("target_selected") else "suggested" if rel.get("target_suggested") else "external"
        lines.append(
            f"    - {rel.get('model')}.{rel.get('field')} -> {rel.get('target_model')}"
            f"  ({rel.get('field_type')}, {marker})"
        )

    lines.append("")
    lines.append(f"  External references: {len(p.get('external_references') or [])}")
    for item in p.get("external_references") or []:
        lines.append(
            f"    - {item.get('model')}  kind={item.get('kind')}  via={item.get('via')}"
            f"  abstract={item.get('abstract')} transient={item.get('transient')}"
        )

    lines.append("")
    lines.append("  High-signal fields:")
    for model, fields in (p.get("high_signal_fields") or {}).items():
        lines.append(f"    [{model}] {len(fields)}")
        for fd in fields[:6]:
            flags = []
            if fd.get("compute"):
                flags.append(f"compute={fd.get('compute')}")
            if fd.get("related"):
                flags.append("related=" + ".".join(str(x) for x in fd.get("related")))
            if fd.get("inherited"):
                flags.append("inherited")
            if fd.get("comodel_name"):
                flags.append(f"comodel={fd.get('comodel_name')}")
            lines.append(f"      - {fd.get('name')} [{fd.get('type')}] {', '.join(flags)}")

    lines.append("")
    lines.append(f"  Suggested context models: {len(p.get('suggested_context_models') or [])}")
    for item in p.get("suggested_context_models") or []:
        lines.append(
            f"    - {item['model']}  reason={item.get('reason')}  via={item.get('via')}"
            f"  abstract={item.get('abstract')} transient={item.get('transient')}"
        )
    if p.get("suggested_next_queries"):
        lines.append("")
        lines.append("  Suggested next queries:")
        for query in p.get("suggested_next_queries") or []:
            lines.append(f"    $ {query}")
    lines.append("")
    lines.append(f"  Result: {p.get('result', 'success')}")
    return "\n".join(lines)


def _h_dump(p: Dict[str, Any]) -> str:
    s = p["summary"]
    r = p["resolve"]
    lines = [_box(f"Dump OK — {p['out_dir']}")]
    lines.append(f"  models    : {s['models']} (abstract {s['abstract_models']}, transient {s['transient_models']})")
    lines.append(f"  fields    : {s['fields']}  (compute {s['fields_computed']}, related {s['fields_related']}, inherited {s['fields_inherited_delegate']})")
    lines.append(f"  fields>=2 modules : {s['fields_multi_module']}")
    lines.append(f"  overrides : {s['methods_with_overrides']} methods, {s['edges_method_overrides']} edges")
    lines.append(f"  depends paths: {s['edges_depends_field']}  -> resolved {r['resolved']} (unresolved {r['unresolved']})")
    return "\n".join(lines)


def emit(payload: Dict[str, Any], kind: str, fmt: str) -> None:
    sys.stdout.write(render(payload, kind, fmt))
    sys.stdout.write("\n")
