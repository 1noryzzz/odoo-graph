from odoo_graph.resolve import resolve_paths
from odoo_graph.tests.fixtures import build_fixture


def test_resolve_paths_walks_comodel_chain(tmp_path):
    out = build_fixture(tmp_path)
    counts = resolve_paths(out)
    assert counts["resolved"] == 2
    assert counts["unresolved"] == 0

    lines = (tmp_path / "edges_resolved.jsonl").read_text().splitlines()
    edges = [__import__("json").loads(l) for l in lines]
    by_path = {e["path"]: e for e in edges}
    # direct path 'name' on same model
    assert by_path["name"]["dst"] == "field::res.partner.name"
    # 2-hop path via parent_id -> res.partner.name
    assert by_path["parent_id.name"]["dst"] == "field::res.partner.name"
    assert len(by_path["parent_id.name"]["steps"]) == 2


def test_resolve_paths_marks_unresolved_when_field_missing(tmp_path):
    import json
    # build and then mangle: remove res.partner.name so path 'name' fails.
    out = build_fixture(tmp_path)
    nodes_path = tmp_path / "nodes.jsonl"
    kept = [
        json.loads(l) for l in nodes_path.read_text().splitlines()
        if "res.partner.name" not in l or "display_name" in l or "parent_name" in l
    ]
    # keep everything except the raw name field node
    nodes = [n for n in kept if n.get("id") != "field::res.partner.name"]
    with nodes_path.open("w") as f:
        for n in nodes:
            f.write(json.dumps(n) + "\n")
    counts = resolve_paths(out)
    # 2 original paths: both hit the missing name eventually -> unresolved=2
    assert counts["unresolved"] == 2
    assert counts["resolved"] == 0
