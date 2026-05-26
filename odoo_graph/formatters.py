"""Output formatters.

`human` prints a compact text tree. `json` emits a single JSON blob to stdout.
`graphviz` is a hook — we keep the registration but raise NotImplementedError
until the user actually needs it.
"""
from __future__ import annotations

import json as _json
import sys
from typing import Any, Dict


FORMATS = ("human", "json", "graphviz")


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
