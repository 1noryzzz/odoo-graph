"""Post-dump resolver: turn FIELD_DEPENDS_ON_PATH strings into concrete
FIELD_DEPENDS_ON_FIELD edges by walking the comodel chain.

Runs on the host Python (no odoo needed). Produces edges_resolved.jsonl.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from .logging import get_logger

log = get_logger(__name__)


def resolve_paths(out_dir: str) -> Dict[str, int]:
    """Resolve dotted depends paths into concrete Field->Field edges.

    Reads $out_dir/{nodes,edges}.jsonl, writes $out_dir/edges_resolved.jsonl.

    Returns a small counters dict so callers can log a summary.
    """
    nodes_path = os.path.join(out_dir, "nodes.jsonl")
    edges_path = os.path.join(out_dir, "edges.jsonl")
    out_path = os.path.join(out_dir, "edges_resolved.jsonl")
    log.debug("resolving paths from %s", out_dir)

    t0 = time.monotonic()
    field_by_key: Dict[tuple, dict] = {}
    with open(nodes_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            n = json.loads(line)
            if n["kind"] == "Field":
                field_by_key[(n["model"], n["name"])] = n
    log.debug("indexed %d field nodes in %.2fs", len(field_by_key), time.monotonic() - t0)

    resolved: List[dict] = []
    unresolved: List[dict] = []
    with open(edges_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if e["kind"] != "FIELD_DEPENDS_ON_PATH":
                continue
            src_id = e["src"]
            root_model = e["root_model"]
            path = e["path"]
            parts = path.split(".")
            cur_model = root_model
            steps: List[dict] = []
            ok = True
            for i, part in enumerate(parts):
                fd = field_by_key.get((cur_model, part))
                if not fd:
                    ok = False
                    unresolved.append({
                        "src": src_id, "path": path,
                        "failed_at": f"{cur_model}.{part}",
                    })
                    break
                steps.append({"model": cur_model, "field": part, "type": fd["type"]})
                if i < len(parts) - 1:
                    comodel = fd.get("comodel_name")
                    if not comodel:
                        ok = False
                        unresolved.append({
                            "src": src_id, "path": path,
                            "failed_at": f"{cur_model}.{part} (non-relational)",
                        })
                        break
                    cur_model = comodel
            if ok:
                leaf = steps[-1]
                resolved.append({
                    "kind": "FIELD_DEPENDS_ON_FIELD",
                    "src": src_id,
                    "dst": f"field::{leaf['model']}.{leaf['field']}",
                    "path": path,
                    "steps": steps,
                })

    with open(out_path, "w", encoding="utf-8") as f:
        for e in resolved:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    elapsed = time.monotonic() - t0
    log.info(
        "resolved %d / %d depends paths into Field->Field edges in %.2fs (unresolved %d)",
        len(resolved), len(resolved) + len(unresolved), elapsed, len(unresolved),
    )
    if unresolved and log.isEnabledFor(10):  # DEBUG
        for u in unresolved[:10]:
            log.debug("unresolved: %s -> %s (%s)", u["src"], u["path"], u["failed_at"])
        if len(unresolved) > 10:
            log.debug("... + %d more unresolved (full list omitted)", len(unresolved) - 10)
    return {"resolved": len(resolved), "unresolved": len(unresolved)}
