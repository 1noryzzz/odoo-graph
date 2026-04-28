from odoo_graph.graph import load_graph
from odoo_graph.resolve import resolve_paths
from odoo_graph.tests.fixtures import build_fixture


def _loaded(tmp_path):
    build_fixture(tmp_path)
    resolve_paths(str(tmp_path))
    return load_graph(str(tmp_path))


def test_field_lineage_upstream_and_downstream(tmp_path):
    g = _loaded(tmp_path)
    l = g.field_lineage("res.partner", "display_name")
    # display_name -> name and -> parent_id.name
    assert len(l["upstream"]) == 2
    paths = {u["path"] for u in l["upstream"]}
    assert paths == {"name", "parent_id.name"}
    # downstream of display_name: nobody depends on it in fixture
    assert l["downstream"] == []

    # name has two inbound deps (display_name uses it via 'name' and 'parent_id.name')
    l2 = g.field_lineage("res.partner", "name")
    assert len(l2["downstream"]) == 2


def test_impact_bfs_finds_downstream(tmp_path):
    g = _loaded(tmp_path)
    hits = g.impact("res.partner", "name", max_depth=2)
    # Two distinct paths converge on the same downstream field (display_name):
    # the BFS stops at the first visit, so 1 unique impacted field.
    fields = {h["field"] for h in hits}
    assert fields == {"field::res.partner.display_name"}


def test_model_summary_groups_fields_by_module(tmp_path):
    g = _loaded(tmp_path)
    s = g.model_summary("res.partner")
    assert s["extended_by_modules"] == ["base", "ext"]
    assert "base" in s["fields_by_module"]
    assert "ext" in s["fields_by_module"]


def test_module_summary_separates_original_vs_extended(tmp_path):
    g = _loaded(tmp_path)
    s_base = g.module_summary("base")
    assert "model::res.partner" in s_base["original_models"]
    s_ext = g.module_summary("ext")
    assert s_ext["original_models"] == []
    assert any(em["model"] == "model::res.partner" for em in s_ext["extended_models"])


def test_overrides_returns_chain(tmp_path):
    g = _loaded(tmp_path)
    md = g.overrides_of("res.partner", "write")
    assert md["override_depth"] == 3
    addons = [c["addon"] for c in md["defined_in_classes"]]
    assert addons == ["ext", "base", None]


def test_find_path_from_model_to_field(tmp_path):
    g = _loaded(tmp_path)
    payload = g.find_path(
        "model::res.partner",
        "field::res.partner.display_name",
        max_depth=2,
        max_paths=2,
    )
    assert payload["paths"]
    assert payload["paths"][0]["nodes"][0] == "model::res.partner"
    assert payload["paths"][0]["nodes"][-1] == "field::res.partner.display_name"
