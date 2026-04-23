"""Tiny synthetic graph fixture for unit tests.

Covers the shapes that came up in the real oabay run:
- a single-module model (base.model_a)
- a two-module model (base.model_b extended by ext.model_b)
- a computed field with @depends on a related m2o chain
- a _inherits delegate field
- a method override chain across 3 addons
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def _write_jsonl(path: Path, items):
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def build_fixture(out_dir: str | os.PathLike) -> str:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    nodes = [
        # modules
        {"kind": "Module", "id": "module::base", "name": "base"},
        {"kind": "Module", "id": "module::ext",  "name": "ext"},
        {"kind": "Module", "id": "module::child", "name": "child"},

        # model A lives in module base
        {"kind": "Model", "id": "model::res.partner", "name": "res.partner",
         "description": "Partner", "abstract": False, "transient": False,
         "original_module": "base", "contributing_modules": ["base", "ext"],
         "inherit": [], "inherits": {}},

        # fields on res.partner
        {"kind": "Field", "id": "field::res.partner.name", "model": "res.partner",
         "name": "name", "type": "char", "store": True, "readonly": False,
         "required": True, "compute": None, "related": None, "inverse": None,
         "comodel_name": None, "module": "base", "modules": ["base"],
         "inherited": False},
        {"kind": "Field", "id": "field::res.partner.display_name",
         "model": "res.partner", "name": "display_name", "type": "char",
         "store": False, "readonly": True, "required": False,
         "compute": "_compute_display_name", "related": None, "inverse": None,
         "comodel_name": None, "module": "ext", "modules": ["base", "ext"],
         "inherited": False},
        {"kind": "Field", "id": "field::res.partner.parent_id",
         "model": "res.partner", "name": "parent_id", "type": "many2one",
         "store": True, "readonly": False, "required": False,
         "compute": None, "related": None, "inverse": None,
         "comodel_name": "res.partner", "module": "base", "modules": ["base"],
         "inherited": False},

        # child model with _inherits delegate
        {"kind": "Model", "id": "model::child.record", "name": "child.record",
         "description": "Delegate", "abstract": False, "transient": False,
         "original_module": "child", "contributing_modules": ["child"],
         "inherit": [], "inherits": {"res.partner": "partner_id"}},
        {"kind": "Field", "id": "field::child.record.partner_id",
         "model": "child.record", "name": "partner_id", "type": "many2one",
         "store": True, "readonly": False, "required": True,
         "compute": None, "related": None, "inverse": None,
         "comodel_name": "res.partner", "module": "child", "modules": ["child"],
         "inherited": False},
        {"kind": "Field", "id": "field::child.record.name",
         "model": "child.record", "name": "name", "type": "char",
         "store": False, "readonly": False, "required": False,
         "compute": None, "related": ["partner_id", "name"], "inverse": None,
         "comodel_name": None, "module": "base", "modules": ["base"],
         "inherited": True, "inherited_from_model": "res.partner"},

        # method with 3-level override
        {"kind": "Method", "id": "method::res.partner.write", "model": "res.partner",
         "name": "write", "override_depth": 3,
         "defined_in_classes": [
             {"class": "Partner", "module": "odoo.addons.ext.models", "addon": "ext"},
             {"class": "Partner", "module": "odoo.addons.base.models", "addon": "base"},
             {"class": "BaseModel", "module": "odoo.models", "addon": None},
         ]},
    ]

    edges = [
        {"kind": "MODULE_DEPENDS_ON_MODULE", "src": "module::ext", "dst": "module::base"},
        {"kind": "MODULE_DEPENDS_ON_MODULE", "src": "module::child", "dst": "module::base"},

        {"kind": "MODULE_DEFINES_MODEL", "src": "module::base", "dst": "model::res.partner", "role": "original"},
        {"kind": "MODULE_DEFINES_MODEL", "src": "module::ext", "dst": "model::res.partner", "role": "extends"},

        {"kind": "MODEL_HAS_FIELD", "src": "model::res.partner", "dst": "field::res.partner.name"},
        {"kind": "MODEL_HAS_FIELD", "src": "model::res.partner", "dst": "field::res.partner.display_name"},
        {"kind": "MODEL_HAS_FIELD", "src": "model::res.partner", "dst": "field::res.partner.parent_id"},

        {"kind": "MODULE_DEFINES_FIELD", "src": "module::base", "dst": "field::res.partner.name", "role": "origin"},
        {"kind": "MODULE_DEFINES_FIELD", "src": "module::ext", "dst": "field::res.partner.display_name", "role": "origin"},
        {"kind": "MODULE_DEFINES_FIELD", "src": "module::base", "dst": "field::res.partner.display_name", "role": "extends"},

        {"kind": "FIELD_RELATES_TO_MODEL", "src": "field::res.partner.parent_id", "dst": "model::res.partner", "ftype": "many2one"},

        {"kind": "FIELD_COMPUTED_BY", "src": "field::res.partner.display_name",
         "dst": "method::res.partner._compute_display_name"},

        # depends path strings
        {"kind": "FIELD_DEPENDS_ON_PATH", "src": "field::res.partner.display_name",
         "root_model": "res.partner", "path": "name"},
        {"kind": "FIELD_DEPENDS_ON_PATH", "src": "field::res.partner.display_name",
         "root_model": "res.partner", "path": "parent_id.name"},

        # override chain
        {"kind": "METHOD_OVERRIDES_METHOD", "src": "method::res.partner.write",
         "dst": "method::res.partner.write", "from_addon": "ext", "to_addon": "base",
         "from_class": "Partner", "to_class": "Partner"},

        # child delegate
        {"kind": "MODEL_DELEGATES_TO_MODEL", "src": "model::child.record",
         "dst": "model::res.partner", "via_field": "partner_id"},
        {"kind": "MODEL_HAS_FIELD", "src": "model::child.record", "dst": "field::child.record.partner_id"},
        {"kind": "MODEL_HAS_FIELD", "src": "model::child.record", "dst": "field::child.record.name"},
    ]

    _write_jsonl(out / "nodes.jsonl", nodes)
    _write_jsonl(out / "edges.jsonl", edges)
    return str(out)
