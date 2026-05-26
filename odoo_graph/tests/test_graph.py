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


def test_field_lineage_reports_delegated_field_analysis(tmp_path):
    g = _loaded(tmp_path)
    l = g.field_lineage("child.record", "name")
    analysis = l["analysis"]
    assert analysis["kind"] == "delegated"
    assert analysis["delegation_chain"][0]["via_field"] == "partner_id"
    assert analysis["delegation_chain"][0]["source_field"] == "res.partner.name"
    assert analysis["writable"] is True
    assert "inverse" not in analysis["writable_reason"]
    assert analysis["shadowing"]["risk"] == "watch"


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


def test_model_summary_reports_delegation_chain(tmp_path):
    g = _loaded(tmp_path)
    s = g.model_summary("child.record")
    assert s["delegation_chain"][0][0]["from_model"] == "child.record"
    assert s["delegation_chain"][0][0]["to_model"] == "res.partner"
    assert s["delegation_chain"][0][0]["via_field"] == "partner_id"


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


def test_find_path_field_to_field_prefers_shortest(tmp_path):
    g = _loaded(tmp_path)
    res = g.find_path(
        start_model="res.partner",
        start_field="display_name",
        target_model="res.partner",
        target_field="name",
        max_depth=3,
    )
    assert res["summary"]["found_paths"] == 1
    p = res["paths"][0]
    assert p["depth"] == 1
    assert p["hops"][0]["edge_kind"] == "FIELD_DEPENDS_ON_FIELD"
    assert p["hops"][0]["path"] in {"name", "parent_id.name"}


def test_find_path_model_scope_start_and_edge_chain(tmp_path):
    g = _loaded(tmp_path)
    res = g.find_path(
        start_model="child.record",
        target_model="res.partner",
        target_field="name",
        max_depth=4,
    )
    assert res["summary"]["found_paths"] == 1
    edge_kinds = [h["edge_kind"] for h in res["paths"][0]["hops"]]
    assert edge_kinds == ["MODEL_DELEGATES_TO_MODEL", "MODEL_HAS_FIELD"]


def test_find_path_respects_edge_kind_whitelist(tmp_path):
    g = _loaded(tmp_path)
    res = g.find_path(
        start_model="child.record",
        target_model="res.partner",
        target_field="name",
        max_depth=4,
        edge_kinds=["FIELD_DEPENDS_ON_FIELD"],
    )
    assert res["summary"]["found_paths"] == 0


def test_find_path_reports_truncated_when_max_paths_reached(tmp_path):
    g = _loaded(tmp_path)
    res = g.find_path(
        start_model="res.partner",
        target_model="res.partner",
        target_field="name",
        max_depth=4,
        max_paths=1,
    )
    assert res["summary"]["found_paths"] == 1
    assert res["truncated"] is True
