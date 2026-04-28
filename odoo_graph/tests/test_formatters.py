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


def test_human_path_output_contains_edges(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    g = load_graph(str(tmp_path))
    payload = g.find_path("model::res.partner", "field::res.partner.display_name")
    out = render(payload, kind="path", fmt="human")
    assert "Path  model::res.partner" in out
    assert "MODEL_HAS_FIELD" in out
