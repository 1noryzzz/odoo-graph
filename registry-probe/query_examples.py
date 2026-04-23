"""
Query the probe output to concretely answer the PRD questions:

1. Can we see cross-module extensions of the SAME model?
2. Can we trace "field F0 changes -> what recomputes?"
3. Can we see override chains on concrete methods?
4. Can we spot fields that multiple modules touch (potential conflicts)?

This only reads the JSONL produced by dump_registry.py. No DB needed.
"""
from __future__ import annotations
import json
import os
from collections import defaultdict

OUT = os.environ.get("REGISTRY_DUMP_DIR", "/workspace/registry-probe/out")

def iter_jsonl(name):
    with open(os.path.join(OUT, name), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

nodes = list(iter_jsonl("nodes.jsonl"))
edges = list(iter_jsonl("edges.jsonl"))

models = {n["id"]: n for n in nodes if n["kind"] == "Model"}
fields = {n["id"]: n for n in nodes if n["kind"] == "Field"}
methods = {n["id"]: n for n in nodes if n["kind"] == "Method"}
modules = {n["id"]: n for n in nodes if n["kind"] == "Module"}

# ---- Q1: multi-module model extensions ------------------------------------
print("=" * 70)
print("Q1: Which models are extended by >=3 modules? (top 15 by breadth)")
print("=" * 70)
multi = []
for m in models.values():
    contrib = m.get("contributing_modules") or []
    if len(contrib) >= 3:
        multi.append((len(contrib), m["name"], contrib))
multi.sort(reverse=True)
for n, name, contrib in multi[:15]:
    print(f"  [{n:>2}] {name:<40} {contrib}")

# ---- Q2: pick res.partner and show cross-module field origins -------------
print()
print("=" * 70)
print("Q2: res.partner field origins by module (top 20 with multi-module)")
print("=" * 70)
target = "res.partner"
rows = []
for fid, fd in fields.items():
    if fd["model"] != target:
        continue
    mods = fd.get("modules") or []
    rows.append((len(mods), fd["name"], fd.get("module"), mods, fd["type"],
                 bool(fd.get("compute")), bool(fd.get("related"))))
rows.sort(reverse=True)
for n, name, origin, mods, ftype, is_compute, is_related in rows[:20]:
    extras = []
    if is_compute: extras.append("compute")
    if is_related: extras.append("related")
    print(f"  [{n}] {name:<30} origin={origin:<18} modules={mods}  type={ftype}  {','.join(extras)}")

# ---- Q3: depends-chain - given a change to res.partner.name, what recomputes?
print()
print("=" * 70)
print("Q3: If res.partner.name changes, which stored/compute fields depend on it?")
print("=" * 70)
# a FIELD_DEPENDS_ON_PATH edge: src=field_id (the dependent), path='a.b.c' rooted at src.model.
# We want anyone whose path starts with 'name' or contains 'partner_id.name' or related chain landing on res.partner.name.
hits = []
for e in edges:
    if e["kind"] != "FIELD_DEPENDS_ON_PATH":
        continue
    path = e.get("path") or ""
    src = e["src"]
    src_field = fields.get(src)
    if not src_field:
        continue
    root_model = e.get("root_model") or src_field["model"]
    # Direct: compute on res.partner depending on 'name'
    if root_model == "res.partner" and (path == "name" or path.endswith(".name")):
        hits.append((src_field["model"], src_field["name"], root_model, path, src_field.get("module")))
    # Cross-model: path walks to partner_id/... name / etc (best-effort substring)
    elif ("partner_id.name" in path or path.endswith(".partner_id.name")):
        hits.append((src_field["model"], src_field["name"], root_model, path, src_field.get("module")))

hits.sort()
for model, name, root, path, mod in hits[:25]:
    print(f"  {model}.{name}  depends on '{path}'  (root={root}, owner-module={mod})")
print(f"  ... total {len(hits)} dependent paths")

# ---- Q4: top overridden methods across addons -----------------------------
print()
print("=" * 70)
print("Q4: Most-overridden methods (chain length >= 3) — top 15")
print("=" * 70)
deep = []
for n in methods.values():
    if n["override_depth"] >= 3:
        deep.append((n["override_depth"], n["model"], n["name"],
                     [c["addon"] for c in n["defined_in_classes"] if c["addon"]]))
deep.sort(reverse=True)
for depth, model, mname, addons in deep[:15]:
    print(f"  depth={depth:>2}  {model}.{mname}  addons={addons}")

# ---- Q5: fields with multiple owning modules (conflict risk)
print()
print("=" * 70)
print("Q5: Fields extended by multiple modules (conflict-watch) — top 15")
print("=" * 70)
multi_f = []
for fd in fields.values():
    mods = fd.get("modules") or []
    if len(mods) >= 2:
        multi_f.append((len(mods), fd["model"], fd["name"], fd.get("module"), mods))
multi_f.sort(reverse=True)
for n, model, name, origin, mods in multi_f[:15]:
    print(f"  [{n}] {model}.{name} origin={origin} modules={mods}")

# ---- Q6: match PRD toy example — one field, multi module override, compute?
print()
print("=" * 70)
print("Q6: PRD example check — pick a compute field with paths crossing modules")
print("=" * 70)
# sale.order.amount_total - known classic compute chain
for fid, fd in fields.items():
    if fd["model"] == "sale.order" and fd["name"] == "amount_total":
        print(f"  sale.order.amount_total:")
        print(f"    origin_module={fd.get('module')}  all_modules={fd.get('modules')}")
        print(f"    type={fd['type']}  compute={fd.get('compute')}  store={fd.get('store')}")
        paths = [e["path"] for e in edges
                 if e["kind"] == "FIELD_DEPENDS_ON_PATH" and e["src"] == fid]
        print(f"    depends paths ({len(paths)}):")
        for p in paths:
            print(f"      - {p}")
        break
