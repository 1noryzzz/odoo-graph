import json
import pytest

from odoo_graph.formatters import render
from odoo_graph.graph import load_graph
from odoo_graph.resolve import resolve_paths
from odoo_graph.tests.fixtures import build_fixture


def test_human_field_output_contains_key_lines(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    g = load_graph(str(tmp_path))
    payload = g.field_lineage("res.partner", "display_name")
    out = render(payload, kind="field", fmt="human")
    assert "res.partner.display_name" in out
    assert "origin-module" in out
    assert "upstream" in out
    assert "parent_id.name" in out


def test_human_field_output_contains_delegation_diagnostics(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    g = load_graph(str(tmp_path))
    payload = g.field_lineage("child.record", "name")
    out = render(payload, kind="field", fmt="human")
    assert "kind          : delegated" in out
    assert "source field  : res.partner.name" in out
    assert "delegation chain" in out
    assert "shadowing risk" in out


def test_human_field_batch_output_is_compact_and_reports_summary():
    payload = {
        "kind": "field_batch",
        "targets": [
            {
                "target": "res.partner.name",
                "status": "found",
                "field": {
                    "model": "res.partner",
                    "name": "name",
                    "type": "char",
                    "module": "base",
                },
                "analysis": {
                    "kind": "local",
                    "storage": "stored",
                    "writable": True,
                    "writable_reason": "stored field",
                },
                "upstream": [],
                "downstream": [],
            },
            {
                "target": "res.partner.nam",
                "status": "not_found",
                "suggestions": ["res.partner.name"],
            },
        ],
        "summary": {"requested": 2, "found": 1, "missing": 1},
    }

    out = render(payload, kind="field_batch", fmt="human")

    assert out.startswith("Field batch  targets=2")
    assert "res.partner.name\n  status: found" in out
    assert "res.partner.nam\n  status: not_found" in out
    assert "Summary:\n  requested: 2\n  found: 1\n  missing: 1" in out
    assert "====" not in out


def test_json_format_is_valid_json(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    g = load_graph(str(tmp_path))
    payload = g.model_summary("res.partner")
    out = render(payload, kind="model", fmt="json")
    parsed = json.loads(out)
    assert parsed["model"]["name"] == "res.partner"


def test_graphviz_is_hooked_but_raises(tmp_path):
    with pytest.raises(NotImplementedError):
        render({"x": 1}, kind="field", fmt="graphviz")


def test_human_path_output_contains_hops(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    g = load_graph(str(tmp_path))
    payload = g.find_path(
        start_model="child.record",
        target_model="res.partner",
        target_field="name",
        max_depth=4,
    )
    out = render(payload, kind="path", fmt="human")
    assert "Path  child.record  ->  res.partner.name" in out
    assert "MODEL_DELEGATES_TO_MODEL" in out
    assert "child.record -> res.partner" in out


def test_human_overrides_batch_output_reports_each_target():
    payload = {
        "kind": "overrides_batch",
        "targets": [
            {
                "target": "res.partner.write",
                "status": "found",
                "override_depth": 1,
                "defined_in_classes": [
                    {
                        "class": "Partner",
                        "addon": "base",
                        "module": "odoo.addons.base.models",
                    }
                ],
            },
            {
                "target": "res.partner.writ",
                "status": "not_found",
                "suggestions": ["res.partner.write"],
            },
        ],
        "summary": {"requested": 2, "found": 1, "missing": 1},
    }

    out = render(payload, kind="overrides_batch", fmt="human")

    assert out.startswith("Override batch  targets=2")
    assert "res.partner.write\n  status: found" in out
    assert "res.partner.writ\n  status: not_found" in out
    assert "Summary:\n  requested: 2\n  found: 1\n  missing: 1" in out


def test_context_human_formatter():
    payload = {
        "mode": "seed",
        "result": "success",
        "requested_models": ["child.record"],
        "selected_models": ["child.record"],
        "missing_models": [],
        "models": [{
            "model": {"name": "child.record", "original_module": "child", "inherit": [], "inherits": {"res.partner": "partner_id"}},
            "fields_by_module": {"child": [{"name": "partner_id"}]},
            "extended_by_modules": ["child"],
        }],
        "relationships": [{"kind": "delegates_to", "from_model": "child.record", "to_model": "res.partner", "via_field": "partner_id", "source": "_inherits"}],
        "suggested_context_models": [{"model": "res.partner", "reason": "delegation parent", "via": "partner_id"}],
        "follow_up_command": "odoo-graph context child.record res.partner --db <db>",
    }
    out = render(payload, kind="context", fmt="human")
    assert "Context  child.record" in out
    assert "Resolved models" in out
    assert "Suggested context models" in out
    assert "Result: success" in out


def test_context_human_formatter_shows_missing_models():
    payload = {
        "mode": "explicit_group",
        "result": "partial",
        "requested_models": ["child.record", "child.recod"],
        "selected_models": ["child.record"],
        "missing_models": [
            {"name": "child.recod", "suggestions": ["child.record"]}
        ],
        "models": [],
        "relationships": [],
        "suggested_context_models": [],
    }

    out = render(payload, kind="context", fmt="human")

    assert "Missing models" in out
    assert "child.recod" in out
    assert "child.record" in out
    assert "Result: partial" in out
