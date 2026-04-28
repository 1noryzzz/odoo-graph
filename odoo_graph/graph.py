"""NetworkX graph wrapper loaded from a dump's JSONL files."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

import networkx as nx

from .logging import get_logger

log = get_logger(__name__)


EDGE_KINDS_FIELD_DEPENDS = "FIELD_DEPENDS_ON_FIELD"
EDGE_KINDS_MODULE_DEPENDS = "MODULE_DEPENDS_ON_MODULE"
EDGE_KINDS_INHERITS = "MODEL_INHERITS_MODEL"
EDGE_KINDS_DELEGATES = "MODEL_DELEGATES_TO_MODEL"
EDGE_KINDS_RELATES = "FIELD_RELATES_TO_MODEL"
EDGE_KINDS_HAS_FIELD = "MODEL_HAS_FIELD"
EDGE_KINDS_DEFINES_MODEL = "MODULE_DEFINES_MODEL"
EDGE_KINDS_DEFINES_FIELD = "MODULE_DEFINES_FIELD"
EDGE_KINDS_COMPUTED_BY = "FIELD_COMPUTED_BY"
EDGE_KINDS_INVERSE_BY = "FIELD_INVERSE_BY"
EDGE_KINDS_OVERRIDES = "METHOD_OVERRIDES_METHOD"


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


@dataclass
class DumpLayout:
    out_dir: Path
    nodes: Path
    edges: Path
    edges_resolved: Path
    summary: Path

    @classmethod
    def at(cls, out_dir: str | os.PathLike) -> "DumpLayout":
        p = Path(out_dir).expanduser().resolve()
        return cls(
            out_dir=p,
            nodes=p / "nodes.jsonl",
            edges=p / "edges.jsonl",
            edges_resolved=p / "edges_resolved.jsonl",
            summary=p / "summary.json",
        )

    def is_valid(self) -> bool:
        return self.nodes.exists() and self.edges.exists()


class OdooGraph:
    """Query-friendly view over a dumped registry graph."""

    def __init__(self, layout: DumpLayout) -> None:
        self.layout = layout
        self.g: nx.MultiDiGraph = nx.MultiDiGraph()
        self._load()

    # -- loading ------------------------------------------------------------
    def _load(self) -> None:
        log.debug("loading dump from %s", self.layout.out_dir)
        t0 = time.monotonic()
        for n in _iter_jsonl(self.layout.nodes):
            self.g.add_node(n["id"], **n)
        for e in _iter_jsonl(self.layout.edges):
            # FIELD_DEPENDS_ON_PATH is intermediate (path-only). We store those
            # as node-level attributes when needed; the resolved form carries dst.
            if "dst" not in e:
                continue
            attrs = {k: v for k, v in e.items() if k not in ("src", "dst")}
            self.g.add_edge(e["src"], e["dst"], **attrs)
        if self.layout.edges_resolved.exists():
            for e in _iter_jsonl(self.layout.edges_resolved):
                attrs = {k: v for k, v in e.items() if k not in ("src", "dst")}
                self.g.add_edge(e["src"], e["dst"], **attrs)
        else:
            log.warning(
                "edges_resolved.jsonl not found at %s; Field->Field queries "
                "will be empty. Re-run `odoo-graph dump` to regenerate.",
                self.layout.edges_resolved,
            )
        log.info(
            "graph loaded: %d nodes / %d edges in %.2fs",
            self.g.number_of_nodes(), self.g.number_of_edges(),
            time.monotonic() - t0,
        )

    # -- lookups ------------------------------------------------------------
    def field_id(self, model: str, name: str) -> str:
        return f"field::{model}.{name}"

    def model_id(self, name: str) -> str:
        return f"model::{name}"

    def module_id(self, name: str) -> str:
        return f"module::{name}"

    def method_id(self, model: str, name: str) -> str:
        return f"method::{model}.{name}"

    def node(self, nid: str) -> Optional[dict]:
        return self.g.nodes.get(nid)

    def nodes_of_kind(self, kind: str) -> Iterator[dict]:
        for _, data in self.g.nodes(data=True):
            if data.get("kind") == kind:
                yield data

    # -- core queries -------------------------------------------------------
    def edges_out(self, nid: str, kind: Optional[str] = None) -> Iterator[tuple]:
        for _, dst, data in self.g.out_edges(nid, data=True):
            if kind is None or data.get("kind") == kind:
                yield dst, data

    def edges_in(self, nid: str, kind: Optional[str] = None) -> Iterator[tuple]:
        for src, _, data in self.g.in_edges(nid, data=True):
            if kind is None or data.get("kind") == kind:
                yield src, data

    def field_lineage(self, model: str, name: str) -> Dict[str, Any]:
        """What this field depends on, and who depends on it."""
        fid = self.field_id(model, name)
        fd = self.node(fid)
        if not fd:
            raise KeyError(f"Field not found: {model}.{name}")
        upstream = []
        for dst, data in self.edges_out(fid, kind=EDGE_KINDS_FIELD_DEPENDS):
            upstream.append({
                "dst": dst, "path": data.get("path"),
                "steps": data.get("steps"),
            })
        downstream = []
        for src, data in self.edges_in(fid, kind=EDGE_KINDS_FIELD_DEPENDS):
            downstream.append({
                "src": src, "path": data.get("path"),
                "steps": data.get("steps"),
            })
        return {"field": fd, "upstream": upstream, "downstream": downstream}

    def impact(
        self,
        model: str,
        name: str,
        max_depth: int = 3,
    ) -> List[dict]:
        """BFS downstream Field->Field edges up to max_depth."""
        fid = self.field_id(model, name)
        if fid not in self.g:
            raise KeyError(f"Field not found: {model}.{name}")
        frontier = [(fid, 0, [])]
        seen = {fid}
        impacted: List[dict] = []
        while frontier:
            nid, depth, path = frontier.pop(0)
            if depth >= max_depth:
                continue
            for src, data in self.edges_in(nid, kind=EDGE_KINDS_FIELD_DEPENDS):
                if src in seen:
                    continue
                seen.add(src)
                new_path = path + [{"via": data.get("path"), "to": nid}]
                impacted.append({
                    "field": src,
                    "depth": depth + 1,
                    "via_path": data.get("path"),
                    "chain": new_path,
                })
                frontier.append((src, depth + 1, new_path))
        return impacted

    def find_field_paths(
        self,
        start_model: str,
        start_name: str,
        target_model: str,
        target_name: str,
        max_depth: int = 4,
        max_paths: int = 20,
    ) -> Dict[str, Any]:
        """Find shortest Field->Field depends paths from start to target.

        Paths follow ``FIELD_DEPENDS_ON_FIELD`` edge direction:
        computed_field -> dependency_field.
        """
        start = self.field_id(start_model, start_name)
        target = self.field_id(target_model, target_name)
        if start not in self.g:
            raise KeyError(f"Field not found: {start_model}.{start_name}")
        if target not in self.g:
            raise KeyError(f"Field not found: {target_model}.{target_name}")

        queue: List[tuple[str, List[dict]]] = [(start, [])]
        shortest_depth: Optional[int] = None
        found: List[List[dict]] = []
        searched_edges = 0
        best_depth: Dict[str, int] = {start: 0}

        while queue:
            nid, hops = queue.pop(0)
            depth = len(hops)
            if shortest_depth is not None and depth >= shortest_depth:
                continue
            if depth >= max_depth:
                continue
            for dst, data in self.edges_out(nid, kind=EDGE_KINDS_FIELD_DEPENDS):
                searched_edges += 1
                next_depth = depth + 1
                prev_depth = best_depth.get(dst)
                if prev_depth is not None and prev_depth < next_depth:
                    continue
                hop = {
                    "src": nid,
                    "dst": dst,
                    "edge_kind": data.get("kind"),
                    "path": data.get("path"),
                }
                new_hops = hops + [hop]
                if dst == target:
                    shortest_depth = len(new_hops)
                    found.append(new_hops)
                    continue
                best_depth[dst] = next_depth
                queue.append((dst, new_hops))

        found.sort(key=lambda p: (len(p), tuple((h["src"], h["dst"], h.get("path")) for h in p)))
        truncated = len(found) > max_paths
        if truncated:
            found = found[:max_paths]

        return {
            "start": {"id": start, "model": start_model, "name": start_name},
            "target": {"id": target, "model": target_model, "name": target_name},
            "paths": [{"hops": p, "length": len(p)} for p in found],
            "max_depth": max_depth,
            "searched_edges": searched_edges,
            "truncated": truncated,
        }

    def model_summary(self, model: str) -> Dict[str, Any]:
        mid = self.model_id(model)
        md = self.node(mid)
        if not md:
            raise KeyError(f"Model not found: {model}")
        fields_by_module: Dict[str, List[dict]] = {}
        for dst, _ in self.edges_out(mid, kind=EDGE_KINDS_HAS_FIELD):
            fd = self.node(dst)
            if not fd:
                continue
            mod = fd.get("module") or "<unknown>"
            fields_by_module.setdefault(mod, []).append(fd)
        inherits = [
            dst for dst, _ in self.edges_out(mid, kind=EDGE_KINDS_INHERITS)
        ]
        delegates = [
            dst for dst, _ in self.edges_out(mid, kind=EDGE_KINDS_DELEGATES)
        ]
        extended_by_modules = md.get("contributing_modules") or []
        return {
            "model": md,
            "inherits": inherits,
            "delegates": delegates,
            "extended_by_modules": extended_by_modules,
            "fields_by_module": fields_by_module,
        }

    def module_summary(self, module: str) -> Dict[str, Any]:
        mid = self.module_id(module)
        md = self.node(mid)
        if not md:
            raise KeyError(f"Module not found: {module}")
        original_models: List[str] = []
        extended_models: List[dict] = []
        for dst, data in self.edges_out(mid, kind=EDGE_KINDS_DEFINES_MODEL):
            role = data.get("role")
            if role == "original":
                original_models.append(dst)
            else:
                extended_models.append({"model": dst, "parent": data.get("parent")})
        original_fields: List[str] = []
        extended_fields: List[str] = []
        for dst, data in self.edges_out(mid, kind=EDGE_KINDS_DEFINES_FIELD):
            role = data.get("role")
            if role == "origin":
                original_fields.append(dst)
            else:
                extended_fields.append(dst)
        depends = [dst for dst, _ in self.edges_out(mid, kind=EDGE_KINDS_MODULE_DEPENDS)]
        return {
            "module": md,
            "depends": depends,
            "original_models": original_models,
            "extended_models": extended_models,
            "original_fields": original_fields,
            "extended_fields": extended_fields,
        }

    def overrides_of(self, model: str, method: str) -> Dict[str, Any]:
        mid = self.method_id(model, method)
        md = self.node(mid)
        if not md:
            raise KeyError(f"Method not found: {model}.{method}")
        return md  # full chain stored as node attribute


def load_graph(out_dir: str) -> OdooGraph:
    layout = DumpLayout.at(out_dir)
    if not layout.is_valid():
        raise FileNotFoundError(
            f"Dump not found at {layout.out_dir}. Run `odoo-graph dump` first."
        )
    return OdooGraph(layout)
