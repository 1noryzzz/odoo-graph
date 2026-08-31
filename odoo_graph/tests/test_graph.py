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


def test_context_summary_seed_suggests_delegation_models(tmp_path):
    g = _loaded(tmp_path)
    s = g.context_summary(["child.record"])
    assert s["mode"] == "seed"
    assert s["result"] == "success"
    assert s["selected_models"] == ["child.record"]
    assert s["missing_models"] == []
    assert any(r["kind"] == "delegates_to" and r["to_model"] == "res.partner" for r in s["relationships"])
    assert s["suggested_context_models"][0]["model"] == "res.partner"
    assert "odoo-graph context child.record res.partner" in s["follow_up_command"]


def test_context_summary_explicit_group_keeps_group_relationships(tmp_path):
    g = _loaded(tmp_path)
    s = g.context_summary(["child.record", "res.partner"])
    assert s["mode"] == "explicit_group"
    assert any(r["kind"] == "delegates_to" for r in s["relationships"])
    assert all(item["model"] != "res.partner" for item in s["suggested_context_models"])
    assert any(item["model"] == "mail.thread" for item in s["suggested_context_models"])


def test_context_summary_reports_inheritance_flags_relations_and_next_queries(tmp_path):
    g = _loaded(tmp_path)
    s = g.context_summary(["child.record"])
    assert any(r["kind"] == "inherits" and r["to_model"] == "mail.thread" for r in s["relationships"])
    mail = next(item for item in s["suggested_context_models"] if item["model"] == "mail.thread")
    assert mail["abstract"] is True
    assert mail["transient"] is False
    assert any(rel["field"] == "partner_id" and rel["target_suggested"] is True for rel in s["relations"])
    assert "child.record" in s["high_signal_fields"]
    assert any(q.startswith("odoo-graph context child.record") for q in s["suggested_next_queries"])


def test_context_summary_dedupes_models_before_mode_selection(tmp_path):
    g = _loaded(tmp_path)
    s = g.context_summary(["child.record", "child.record"])
    assert s["mode"] == "seed"
    assert s["requested_models"] == ["child.record"]


def test_context_summary_explicit_group_returns_partial_results(tmp_path):
    g = _loaded(tmp_path)

    s = g.context_summary(["child.record", "res.parner", "res.partner"])

    assert s["result"] == "partial"
    assert s["requested_models"] == [
        "child.record",
        "res.parner",
        "res.partner",
    ]
    assert s["selected_models"] == ["child.record", "res.partner"]
    assert s["missing_models"][0]["name"] == "res.parner"
    assert s["missing_models"][0]["suggestions"][0] == "res.partner"
    assert len(s["missing_models"][0]["suggestions"]) <= 3
    assert any(r["kind"] == "delegates_to" for r in s["relationships"])


def test_context_summary_all_missing_is_actionable_not_found(tmp_path):
    g = _loaded(tmp_path)

    s = g.context_summary(["res.parner", "child.recod"])

    assert s["result"] == "not_found"
    assert s["selected_models"] == []
    assert [item["name"] for item in s["missing_models"]] == [
        "res.parner",
        "child.recod",
    ]
    assert s["missing_models"][0]["suggestions"][0] == "res.partner"
    assert s["missing_models"][1]["suggestions"][0] == "child.record"
    assert all(len(item["suggestions"]) <= 3 for item in s["missing_models"])
