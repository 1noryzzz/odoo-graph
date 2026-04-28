"""NetworkX graph wrapper loaded from a dump's JSONL files."""
from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from collections import deque
from typing import Any, Deque, Dict, Iterable, Iterator, List, Optional, Set, Tuple

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
EDGE_KINDS_PATH_DEFAULT = (
    EDGE_KINDS_FIELD_DEPENDS,
    EDGE_KINDS_HAS_FIELD,
    EDGE_KINDS_RELATES,
    EDGE_KINDS_DELEGATES,
    EDGE_KINDS_INHERITS,
)


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

    def find_path(
        self,
        start_model: str,
        target_model: str,
        target_field: str,
        *,
        start_field: Optional[str] = None,
        max_depth: int = 6,
        edge_kinds: Optional[Iterable[str]] = None,
        max_paths: int = 3,
    ) -> Dict[str, Any]:
        """Find explainable shortest paths (BFS) toward a target field.

        When ``start_field`` is omitted, this starts from all fields owned by
        ``start_model`` (MODEL_HAS_FIELD outgoing edges).
        """
        if max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if max_paths <= 0:
            raise ValueError("max_paths must be >= 1")

        default_edge_kinds = [
            EDGE_KINDS_FIELD_DEPENDS,
            EDGE_KINDS_RELATES,
            EDGE_KINDS_HAS_FIELD,
            EDGE_KINDS_DELEGATES,
            EDGE_KINDS_INHERITS,
        ]
        allowed_kinds = set(edge_kinds or default_edge_kinds)
        target_id = self.field_id(target_model, target_field)
        if target_id not in self.g:
            raise KeyError(f"Field not found: {target_model}.{target_field}")

        start_ids: List[str] = []
        if start_field:
            sid = self.field_id(start_model, start_field)
            if sid not in self.g:
                raise KeyError(f"Field not found: {start_model}.{start_field}")
            start_ids = [sid]
        else:
            smid = self.model_id(start_model)
            if smid not in self.g:
                raise KeyError(f"Model not found: {start_model}")
            start_ids = [smid]
            start_ids.extend(
                dst for dst, _ in self.edges_out(smid, kind=EDGE_KINDS_HAS_FIELD)
                if dst in self.g
            )

        kind_priority = {
            EDGE_KINDS_FIELD_DEPENDS: 0,
            EDGE_KINDS_RELATES: 1,
            EDGE_KINDS_HAS_FIELD: 2,
            EDGE_KINDS_DELEGATES: 3,
            EDGE_KINDS_INHERITS: 9,  # low priority
        }

        queue: Deque[Tuple[str, int, List[dict]]] = deque()
        visited: Set[str] = set()
        paths: List[Dict[str, Any]] = []

        for sid in start_ids:
            queue.append((sid, 0, []))
            visited.add(sid)

        while queue and len(paths) < max_paths:
            nid, depth, hops = queue.popleft()
            if nid == target_id:
                paths.append(
                    {
                        "start": hops[0]["src"] if hops else nid,
                        "target": target_id,
                        "depth": depth,
                        "hops": hops,
                    }
                )
                continue
            if depth >= max_depth:
                continue

            neighbors = []
            for _, dst, data in self.g.out_edges(nid, data=True):
                kind = data.get("kind")
                if kind not in allowed_kinds:
                    continue
                neighbors.append((dst, data))

            neighbors.sort(key=lambda x: kind_priority.get(x[1].get("kind"), 5))

            for dst, data in neighbors:
                if dst in visited:
                    continue
                visited.add(dst)
                hop = {
                    "src": nid,
                    "dst": dst,
                    "edge_kind": data.get("kind"),
                    "path": data.get("path"),
                }
                queue.append((dst, depth + 1, hops + [hop]))

        truncated = bool(queue) and len(paths) >= max_paths
        return {
            "paths": paths,
            "truncated": truncated,
            "summary": {
                "start_model": start_model,
                "start_field": start_field,
                "target_model": target_model,
                "target_field": target_field,
                "max_depth": max_depth,
                "edge_kinds": sorted(allowed_kinds),
                "max_paths": max_paths,
                "found_paths": len(paths),
            },
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

    def find_path(
        self,
        start_nid: str,
        target_nid: str,
        *,
        max_depth: int = 6,
        max_paths: int = 3,
        allow_kinds: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Find up to ``max_paths`` shortest directed paths from start to target."""
        if start_nid not in self.g:
            raise KeyError(f"Start node not found: {start_nid}")
        if target_nid not in self.g:
            raise KeyError(f"Target node not found: {target_nid}")

        allowed = tuple(allow_kinds) if allow_kinds else EDGE_KINDS_PATH_DEFAULT
        q = deque([(start_nid, [start_nid], [])])
        seen_depth = {start_nid: 0}
        results: List[Dict[str, Any]] = []

        while q and len(results) < max_paths:
            nid, nodes_path, edges_path = q.popleft()
            depth = len(edges_path)
            if nid == target_nid:
                results.append({"nodes": nodes_path, "edges": edges_path, "depth": depth})
                continue
            if depth >= max_depth:
                continue
            for _, dst, data in self.g.out_edges(nid, data=True):
                kind = data.get("kind")
                if kind not in allowed:
                    continue
                next_depth = depth + 1
                known = seen_depth.get(dst)
                if known is not None and known < next_depth:
                    continue
                seen_depth[dst] = next_depth
                q.append(
                    (
                        dst,
                        nodes_path + [dst],
                        edges_path + [{"src": nid, "dst": dst, "kind": kind, "path": data.get("path")}],
                    )
                )
        return {
            "start": start_nid,
            "target": target_nid,
            "max_depth": max_depth,
            "max_paths": max_paths,
            "allow_kinds": list(allowed),
            "paths": results,
        }


def load_graph(out_dir: str) -> OdooGraph:
    layout = DumpLayout.at(out_dir)
    if not layout.is_valid():
        raise FileNotFoundError(
            f"Dump not found at {layout.out_dir}. Run `odoo-graph dump` first."
        )
    return OdooGraph(layout)
