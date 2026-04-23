"""Post-dump resolver: turn FIELD_DEPENDS_ON_PATH strings into concrete
FIELD_DEPENDS_ON_FIELD edges by walking the comodel chain.

Runs on the host Python (no odoo needed). Produces edges_resolved.jsonl.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


def resolve_paths(out_dir: str) -> Dict[str, int]:
    """Resolve dotted depends paths into concrete Field->Field edges.

    Reads $out_dir/{nodes,edges}.jsonl, writes $out_dir/edges_resolved.jsonl.

    Returns a small counters dict so callers can log a summary.
    """
    nodes_path = os.path.join(out_dir, "nodes.jsonl")
    edges_path = os.path.join(out_dir, "edges.jsonl")
    out_path = os.path.join(out_dir, "edges_resolved.jsonl")

    field_by_key: Dict[tuple, dict] = {}
    with open(nodes_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            n = json.loads(line)
            if n["kind"] == "Field":
                field_by_key[(n["model"], n["name"])] = n

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

    return {"resolved": len(resolved), "unresolved": len(unresolved)}
