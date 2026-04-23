"""
Odoo Registry Runtime Probe - Demo
==================================

Goal: validate that env.registry exposes enough runtime state to build a
"module -> model -> field/method" dependency graph for Odoo 17.

Run via Odoo's shell interface:

    PYTHONPATH=./odoo-17.0 .venv/bin/python odoo-17.0/odoo-bin shell \
        -d odoo_demo \
        --db_host=127.0.0.1 -r odoo -w odoo \
        --addons-path=./odoo-17.0/addons \
        --no-http \
        < registry-probe/dump_registry.py

The script reads from env.registry only (no DB writes), and emits JSONL
node/edge files plus a summary report.
"""
from __future__ import annotations

import json
import inspect
import os
from collections import defaultdict

current_dir = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("REGISTRY_DUMP_DIR", f"{current_dir}/out")
os.makedirs(OUT_DIR, exist_ok=True)


def jsonl_writer(path):
    f = open(path, "w", encoding="utf-8")

    def _write(obj):
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True))
        f.write("\n")

    return f, _write


def safe(val):
    if val is None or isinstance(val, (bool, int, float, str)):
        return val
    if isinstance(val, (list, tuple, set, frozenset)):
        return [safe(v) for v in val]
    if isinstance(val, dict):
        return {str(k): safe(v) for k, v in val.items()}
    return repr(val)


# `env` is pre-populated by odoo-bin shell
registry = env.registry  # noqa: F821
print(f"[probe] registry has {len(registry.models)} model classes")
print(f"[probe] field_depends entries: {len(registry.field_depends)}")

nodes_f, emit_node = jsonl_writer(os.path.join(OUT_DIR, "nodes.jsonl"))
edges_f, emit_edge = jsonl_writer(os.path.join(OUT_DIR, "edges.jsonl"))

summary = {
    "models": 0,
    "abstract_models": 0,
    "transient_models": 0,
    "fields": 0,
    "fields_multi_module": 0,
    "fields_computed": 0,
    "fields_related": 0,
    "fields_inverse": 0,
    "methods_with_overrides": 0,
    "edges_depends_field": 0,
    "edges_has_field": 0,
    "edges_relates_to": 0,
    "edges_inherits_model": 0,
    "edges_delegates_to_model": 0,
    "edges_module_defines_model": 0,
    "edges_module_depends": 0,
    "edges_method_overrides": 0,
}

modules_seen = set()

MODULE_META = {}
for mod_name in env.registry._init_modules:  # set, not ordered
    modules_seen.add(mod_name)

irmod = env["ir.module.module"].sudo()
installed = irmod.search([("state", "=", "installed")])
for m in installed:
    modules_seen.add(m.name)
    MODULE_META[m.name] = {
        "shortdesc": m.shortdesc,
        "author": m.author,
        "category": m.category_id.display_name if m.category_id else None,
        "depends": [d.name for d in m.dependencies_id],
    }

for mod_name in sorted(modules_seen):
    meta = MODULE_META.get(mod_name, {})
    emit_node({
        "kind": "Module",
        "id": f"module::{mod_name}",
        "name": mod_name,
        "shortdesc": meta.get("shortdesc"),
        "category": meta.get("category"),
    })
    for dep in meta.get("depends", []):
        emit_edge({
            "kind": "MODULE_DEPENDS_ON_MODULE",
            "src": f"module::{mod_name}",
            "dst": f"module::{dep}",
        })
        summary["edges_module_depends"] += 1


for model_name, ModelCls in sorted(registry.models.items()):
    summary["models"] += 1
    is_abstract = bool(getattr(ModelCls, "_abstract", False))
    is_transient = bool(getattr(ModelCls, "_transient", False))
    if is_abstract:
        summary["abstract_models"] += 1
    if is_transient:
        summary["transient_models"] += 1

    original_module = getattr(ModelCls, "_original_module", None)
    inherit_module = dict(getattr(ModelCls, "_inherit_module", {}) or {})
    inherit_names = list(getattr(ModelCls, "_inherit", ()) or ())
    inherits_map = dict(getattr(ModelCls, "_inherits", {}) or {})

    contributing_modules = set()
    if original_module:
        contributing_modules.add(original_module)
    contributing_modules.update(inherit_module.values())

    emit_node({
        "kind": "Model",
        "id": f"model::{model_name}",
        "name": model_name,
        "description": getattr(ModelCls, "_description", None),
        "table": getattr(ModelCls, "_table", None),
        "abstract": is_abstract,
        "transient": is_transient,
        "original_module": original_module,
        "contributing_modules": sorted(contributing_modules),
        "inherit": inherit_names,
        "inherits": inherits_map,
    })

    if original_module:
        emit_edge({
            "kind": "MODULE_DEFINES_MODEL",
            "src": f"module::{original_module}",
            "dst": f"model::{model_name}",
            "role": "original",
        })
        summary["edges_module_defines_model"] += 1
    for parent, mod in inherit_module.items():
        if mod and mod != original_module:
            emit_edge({
                "kind": "MODULE_DEFINES_MODEL",
                "src": f"module::{mod}",
                "dst": f"model::{model_name}",
                "role": "extends",
                "parent": parent,
            })
            summary["edges_module_defines_model"] += 1

    for parent in inherit_names:
        if parent == model_name:
            continue
        if parent not in registry.models:
            continue
        emit_edge({
            "kind": "MODEL_INHERITS_MODEL",
            "src": f"model::{model_name}",
            "dst": f"model::{parent}",
            "via_module": inherit_module.get(parent),
        })
        summary["edges_inherits_model"] += 1

    for parent, fk in inherits_map.items():
        emit_edge({
            "kind": "MODEL_DELEGATES_TO_MODEL",
            "src": f"model::{model_name}",
            "dst": f"model::{parent}",
            "via_field": fk,
        })
        summary["edges_delegates_to_model"] += 1

    for fname, field in ModelCls._fields.items():
        summary["fields"] += 1
        f_module = getattr(field, "_module", None)
        f_modules = list(getattr(field, "_modules", ()) or ())
        if len(f_modules) > 1:
            summary["fields_multi_module"] += 1
        if field.compute:
            summary["fields_computed"] += 1
        if field.related:
            summary["fields_related"] += 1
        if field.inverse:
            summary["fields_inverse"] += 1

        field_id = f"field::{model_name}.{fname}"
        emit_node({
            "kind": "Field",
            "id": field_id,
            "model": model_name,
            "name": fname,
            "type": field.type,
            "store": bool(field.store),
            "readonly": bool(field.readonly),
            "required": bool(field.required),
            "compute": getattr(field, "compute", None) if isinstance(field.compute, str) else (field.compute.__name__ if field.compute else None),
            "related": list(getattr(field, "related", ()) or ()) if field.related else None,
            "inverse": field.inverse.__name__ if field.inverse and not isinstance(field.inverse, str) else field.inverse,
            "comodel_name": getattr(field, "comodel_name", None),
            "inverse_name": getattr(field, "inverse_name", None),
            "module": f_module,
            "modules": f_modules,
            "depends_context": list(registry.field_depends_context.get(field, ()) or ()),
        })

        emit_edge({
            "kind": "MODEL_HAS_FIELD",
            "src": f"model::{model_name}",
            "dst": field_id,
        })
        summary["edges_has_field"] += 1

        if f_module:
            emit_edge({
                "kind": "MODULE_DEFINES_FIELD",
                "src": f"module::{f_module}",
                "dst": field_id,
                "role": "origin",
            })
        for m in f_modules:
            if m and m != f_module:
                emit_edge({
                    "kind": "MODULE_DEFINES_FIELD",
                    "src": f"module::{m}",
                    "dst": field_id,
                    "role": "extends",
                })

        comodel = getattr(field, "comodel_name", None)
        if comodel and comodel in registry.models:
            emit_edge({
                "kind": "FIELD_RELATES_TO_MODEL",
                "src": field_id,
                "dst": f"model::{comodel}",
                "ftype": field.type,
            })
            summary["edges_relates_to"] += 1

        # compute/inverse method targets
        if field.compute:
            m_name = field.compute if isinstance(field.compute, str) else getattr(field.compute, "__name__", None)
            if m_name:
                meth_id = f"method::{model_name}.{m_name}"
                emit_edge({
                    "kind": "FIELD_COMPUTED_BY",
                    "src": field_id,
                    "dst": meth_id,
                })
        if field.inverse and not isinstance(field.inverse, str):
            m_name = getattr(field.inverse, "__name__", None)
            if m_name:
                meth_id = f"method::{model_name}.{m_name}"
                emit_edge({
                    "kind": "FIELD_INVERSE_BY",
                    "src": field_id,
                    "dst": meth_id,
                })

        # depends_field edges - computed depend paths are on the owning model
        for dep_path in registry.field_depends.get(field, ()) or ():
            emit_edge({
                "kind": "FIELD_DEPENDS_ON_PATH",
                "src": field_id,
                "path": dep_path,
                "root_model": model_name,
            })
            summary["edges_depends_field"] += 1


# Methods + override inference (MRO walk)
# Only look at model classes in the registry to capture @api.model, override chains.
# We collect a method edge when the same name appears in multiple bases.
method_override_groups = defaultdict(list)  # (model, method_name) -> [(class_module, class_qualname)]

for model_name, ModelCls in sorted(registry.models.items()):
    # Collect candidate method names defined anywhere in MRO (excluding object/BaseModel)
    seen_names = set()
    for base in ModelCls.__mro__:
        base_module = base.__module__ or ""
        if not base_module.startswith("odoo.addons.") and not base_module.endswith(".models"):
            # skip non-addon bases (BaseModel / MetaModel / object)
            continue
        for name, attr in base.__dict__.items():
            if name.startswith("__"):
                continue
            if not callable(attr) and not isinstance(attr, (classmethod, staticmethod)):
                continue
            if name in ModelCls._fields:
                continue
            seen_names.add(name)

    for mname in seen_names:
        chain = []
        for base in ModelCls.__mro__:
            if mname in base.__dict__:
                base_module = base.__module__ or ""
                # Extract addon module if any
                addon = None
                if base_module.startswith("odoo.addons."):
                    addon = base_module.split(".")[2]
                chain.append({
                    "class": base.__qualname__,
                    "module": base_module,
                    "addon": addon,
                })
        if not chain:
            continue

        meth_id = f"method::{model_name}.{mname}"
        emit_node({
            "kind": "Method",
            "id": meth_id,
            "model": model_name,
            "name": mname,
            "defined_in_classes": chain,
            "override_depth": len(chain),
        })
        if len(chain) >= 2:
            summary["methods_with_overrides"] += 1
            # chain[0] overrides chain[1] overrides chain[2] ...
            for i in range(len(chain) - 1):
                emit_edge({
                    "kind": "METHOD_OVERRIDES_METHOD",
                    "src": meth_id,
                    "dst": meth_id,
                    "from_class": chain[i]["class"],
                    "to_class": chain[i + 1]["class"],
                    "from_addon": chain[i]["addon"],
                    "to_addon": chain[i + 1]["addon"],
                })
                summary["edges_method_overrides"] += 1

nodes_f.close()
edges_f.close()

summary_path = os.path.join(OUT_DIR, "summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("[probe] wrote:", os.path.join(OUT_DIR, "nodes.jsonl"))
print("[probe] wrote:", os.path.join(OUT_DIR, "edges.jsonl"))
print("[probe] summary:", json.dumps(summary, indent=2))
