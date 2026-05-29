"""
Resolve FIELD_DEPENDS_ON_PATH (dotted path string) into concrete
FIELD_DEPENDS_ON_FIELD edges by walking the comodel chain.

This is the piece that turns `order_line.price_subtotal` into:
  sale.order.amount_total -> (via sale.order.order_line) -> sale.order.line.price_subtotal

Run standalone after dump_registry.py produced out/*.jsonl.
"""
from __future__ import annotations
import json
import os
from collections import defaultdict

current_dir = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("REGISTRY_DUMP_DIR", f"{current_dir}/out")

def iter_jsonl(name):
    with open(os.path.join(OUT, name), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

nodes = list(iter_jsonl("nodes.jsonl"))
edges = list(iter_jsonl("edges.jsonl"))

# Build lookups
field_by_key = {}    # (model, name) -> field node
for n in nodes:
    if n["kind"] == "Field":
        field_by_key[(n["model"], n["name"])] = n

resolved_edges = []
unresolved = []

for e in edges:
    if e["kind"] != "FIELD_DEPENDS_ON_PATH":
        continue
    src_id = e["src"]
    # src_id is field::<model>.<name>. root_model equals the field's owning model.
    root_model = e["root_model"]
    path = e["path"]
    parts = path.split(".")
    cur_model = root_model
    steps = []
    ok = True
    for i, part in enumerate(parts):
        fd = field_by_key.get((cur_model, part))
        if not fd:
            ok = False
            unresolved.append({"src": src_id, "path": path, "failed_at": f"{cur_model}.{part}"})
            break
        steps.append({"model": cur_model, "field": part, "type": fd["type"]})
        is_last = (i == len(parts) - 1)
        if not is_last:
            comodel = fd.get("comodel_name")
            if not comodel:
                ok = False
                unresolved.append({"src": src_id, "path": path, "failed_at": f"{cur_model}.{part} (not relational)"})
                break
            cur_model = comodel
    if ok:
        leaf = steps[-1]
        resolved_edges.append({
            "kind": "FIELD_DEPENDS_ON_FIELD",
            "src": src_id,
            "dst": f"field::{leaf['model']}.{leaf['field']}",
            "path": path,
            "steps": steps,
        })

out_path = os.path.join(OUT, "edges_resolved.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for e in resolved_edges:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

print(f"Resolved {len(resolved_edges)} FIELD_DEPENDS_ON_FIELD edges; {len(unresolved)} unresolved")

# Sample lineage: what affects sale.order.amount_total, and follow it back one hop?
target = "field::sale.order.amount_total"
print("\nLineage incoming to sale.order.amount_total:")
for e in resolved_edges:
    if e["src"] == target:
        hops = " -> ".join([f"{s['model']}.{s['field']}" for s in e["steps"]])
        print(f"  via '{e['path']}':  sale.order.amount_total <- {hops}")

# Sample: what happens if we touch sale.order.line.price_subtotal?
print("\nDownstream recomputes if sale.order.line.price_subtotal changes:")
dst = "field::sale.order.line.price_subtotal"
for e in resolved_edges:
    if e["dst"] == dst:
        print(f"  {e['src'].replace('field::','')}  <=depends=  via path '{e['path']}'")

# Unresolved samples
print("\nUnresolved sample (first 5):")
for u in unresolved[:5]:
    print(f"  {u}")
print(f"Total unresolved paths: {len(unresolved)}")
