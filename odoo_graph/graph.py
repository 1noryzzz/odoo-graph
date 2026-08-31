"""NetworkX graph wrapper loaded from a dump's JSONL files."""
from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
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
        analysis = self._field_analysis(fd, upstream)
        return {
            "field": fd,
            "analysis": analysis,
            "upstream": upstream,
            "downstream": downstream,
        }

    def _field_analysis(self, fd: Dict[str, Any], upstream: List[dict]) -> Dict[str, Any]:
        related_path = self._related_path(fd)
        delegation_chain = self._field_delegation_chain(
            fd["model"],
            fd["name"],
        )
        has_delegation = bool(delegation_chain)

        if has_delegation and fd.get("compute") == "_compute_related":
            kind = "delegated_related"
        elif has_delegation or fd.get("inherited"):
            kind = "delegated"
        elif fd.get("related"):
            kind = "related"
        elif fd.get("compute"):
            kind = "computed"
        else:
            kind = "local"

        source_field = self._effective_source_field(fd["model"], fd["name"])
        if not source_field and delegation_chain:
            source_field = delegation_chain[-1].get("source_field")

        return {
            "kind": kind,
            "declared_on_model": kind == "local",
            "storage": "stored" if fd.get("store") else "non-stored",
            "related_path": related_path,
            "source_field": source_field,
            "writable": not bool(fd.get("readonly")),
            "writable_reason": self._writable_reason(fd, kind),
            "delegation_chain": delegation_chain,
            "shadowing": self._shadowing_risk(fd, delegation_chain),
        }

    def _effective_source_field(
        self,
        model: str,
        name: str,
        seen: Optional[Set[str]] = None,
    ) -> Optional[str]:
        fid = self.field_id(model, name)
        if seen is None:
            seen = set()
        if fid in seen:
            return fid.replace("field::", "")
        seen.add(fid)

        next_fields = []
        for dst, _ in self.edges_out(fid, kind=EDGE_KINDS_FIELD_DEPENDS):
            parsed = self._parse_field_id(dst)
            if parsed:
                next_fields.append(parsed)
        if not next_fields:
            return None
        next_model, next_name = next_fields[0]
        deeper = self._effective_source_field(next_model, next_name, seen)
        return deeper or f"{next_model}.{next_name}"

    def _related_path(self, fd: Dict[str, Any]) -> List[str]:
        related = fd.get("related")
        if not related:
            return []
        if isinstance(related, str):
            return [p for p in related.split(".") if p]
        if isinstance(related, list):
            # Older dumps may serialize a related string as a list of chars.
            if all(isinstance(p, str) and len(p) == 1 for p in related):
                return [p for p in "".join(related).split(".") if p]
            return [str(p) for p in related if p]
        return []

    def _writable_reason(self, fd: Dict[str, Any], kind: str) -> str:
        if fd.get("readonly"):
            return "not writable: field is readonly"
        if fd.get("inverse"):
            return f"writable: {kind} field has inverse {fd['inverse']}"
        if fd.get("related"):
            return "writable: related field is not readonly"
        if fd.get("compute"):
            return "writable: computed field is not readonly"
        if fd.get("store"):
            return "writable: stored field is not readonly"
        return "writable: field is not readonly"

    def _delegate_edges_by_field(self, model: str) -> Dict[str, Tuple[str, dict]]:
        out: Dict[str, Tuple[str, dict]] = {}
        for dst, data in self.edges_out(self.model_id(model), kind=EDGE_KINDS_DELEGATES):
            via = data.get("via_field")
            if via:
                out[str(via)] = (dst.replace("model::", ""), data)
        return out

    def _parse_field_id(self, fid: str) -> Optional[Tuple[str, str]]:
        if not fid.startswith("field::"):
            return None
        raw = fid.replace("field::", "", 1)
        model, _, name = raw.rpartition(".")
        if not model or not name:
            return None
        return model, name

    def _field_delegation_chain(
        self,
        model: str,
        name: str,
        seen: Optional[Set[str]] = None,
    ) -> List[dict]:
        fid = self.field_id(model, name)
        if seen is None:
            seen = set()
        if fid in seen:
            return []
        seen.add(fid)

        delegates = self._delegate_edges_by_field(model)
        for dst, data in self.edges_out(fid, kind=EDGE_KINDS_FIELD_DEPENDS):
            path = str(data.get("path") or "")
            first = path.split(".", 1)[0]
            if first not in delegates:
                continue
            target_model, _ = delegates[first]
            parsed = self._parse_field_id(dst)
            if not parsed:
                continue
            source_model, source_name = parsed
            hop = {
                "from_model": model,
                "field": name,
                "to_model": target_model,
                "via_field": first,
                "path": path,
                "source": "_inherits",
                "source_field": f"{source_model}.{source_name}",
            }
            return [hop] + self._field_delegation_chain(
                source_model,
                source_name,
                seen,
            )
        fd = self.node(fid)
        if fd:
            related_path = self._related_path(fd)
            if len(related_path) >= 2 and related_path[0] in delegates:
                target_model, _ = delegates[related_path[0]]
                source_name = related_path[-1]
                source_field = self.field_id(target_model, source_name)
                if self.node(source_field) is not None:
                    hop = {
                        "from_model": model,
                        "field": name,
                        "to_model": target_model,
                        "via_field": related_path[0],
                        "path": ".".join(related_path),
                        "source": "_inherits",
                        "source_field": f"{target_model}.{source_name}",
                    }
                    return [hop] + self._field_delegation_chain(
                        target_model,
                        source_name,
                        seen,
                    )
        return []

    def _shadowing_risk(
        self,
        fd: Dict[str, Any],
        delegation_chain: List[dict],
    ) -> Dict[str, Any]:
        model = fd["model"]
        name = fd["name"]
        candidates = []
        for chain in self._delegation_chains(model):
            if self.node(self.field_id(chain[-1]["to_model"], name)) is not None:
                candidates.append({
                    "model": chain[-1]["to_model"],
                    "field": f"{chain[-1]['to_model']}.{name}",
                    "via_path": ".".join(h["via_field"] for h in chain),
                })

        if not candidates:
            return {
                "risk": "none",
                "reason": "no same-name field found on delegated parents",
                "candidates": [],
            }
        if not delegation_chain and not fd.get("inherited"):
            return {
                "risk": "high",
                "reason": "local field has the same name as delegated parent field(s)",
                "candidates": candidates,
            }
        return {
            "risk": "watch",
            "reason": "field is resolved through same-name delegated parent field(s)",
            "candidates": candidates,
        }

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
            "delegation_chain": self._delegation_chains(model),
            "extended_by_modules": extended_by_modules,
            "fields_by_module": fields_by_module,
        }

    def _delegation_chains(self, model: str) -> List[List[dict]]:
        chains: List[List[dict]] = []

        def walk(current: str, prefix: List[dict], seen: Set[str]) -> None:
            for dst, data in self.edges_out(
                self.model_id(current),
                kind=EDGE_KINDS_DELEGATES,
            ):
                to_model = dst.replace("model::", "")
                if to_model in seen:
                    continue
                hop = {
                    "from_model": current,
                    "to_model": to_model,
                    "via_field": data.get("via_field"),
                    "source": "_inherits",
                    "path": ".".join(
                        [h["via_field"] for h in prefix if h.get("via_field")]
                        + ([data.get("via_field")] if data.get("via_field") else [])
                    ),
                }
                chain = prefix + [hop]
                chains.append(chain)
                walk(to_model, chain, seen | {to_model})

        walk(model, [], {model})
        return chains

    def context_summary(self, models: List[str]) -> Dict[str, Any]:
        if not models:
            raise ValueError("context requires at least one model")
        requested = list(dict.fromkeys(models))
        selected = [m for m in requested if self.node(self.model_id(m))]
        missing_names = [m for m in requested if m not in selected]
        model_names = sorted(n["name"] for n in self.nodes_of_kind("Model"))
        missing = [
            {
                "name": model,
                "suggestions": get_close_matches(
                    model,
                    model_names,
                    n=3,
                    cutoff=0.5,
                ),
            }
            for model in missing_names
        ]
        result = (
            "success"
            if not missing
            else "partial"
            if selected
            else "not_found"
        )
        seed_mode = len(requested) == 1
        requested_set = set(selected)
        model_summaries = [self.model_summary(m) for m in selected]

        relationships: List[Dict[str, Any]] = []
        relations: List[Dict[str, Any]] = []
        external_references: List[Dict[str, Any]] = []
        suggestions: Dict[str, Dict[str, Any]] = {}

        def model_flags(model: str) -> Dict[str, Any]:
            md = self.node(self.model_id(model)) or {}
            return {
                "abstract": bool(md.get("abstract")),
                "transient": bool(md.get("transient")),
            }

        def add_external(kind: str, model: str, via: str | None, reason: str) -> None:
            if model in requested_set or not self.node(self.model_id(model)):
                return
            item = {"kind": kind, "model": model, "via": via, "reason": reason}
            item.update(model_flags(model))
            if item not in external_references:
                external_references.append(item)

        def add_suggestion(model: str, reason: str, via: str | None, score: int) -> None:
            if model in requested_set or not self.node(self.model_id(model)):
                return
            current = suggestions.get(model)
            if current is None or score > current["score"]:
                item = {"model": model, "reason": reason, "via": via, "score": score}
                item.update(model_flags(model))
                suggestions[model] = item

        for model in selected:
            mid = self.model_id(model)
            for dst, _data in self.edges_out(mid, kind=EDGE_KINDS_INHERITS):
                other = dst.replace("model::", "")
                rel = {"kind": "inherits", "from_model": model, "to_model": other, "source": "_inherit"}
                if seed_mode or other in requested_set:
                    relationships.append(rel)
                add_external("inheritance_parent", other, "_inherit", "inheritance parent")
                add_suggestion(other, "inheritance parent", "_inherit", 90)
            for src, _data in self.edges_in(mid, kind=EDGE_KINDS_INHERITS):
                other = src.replace("model::", "")
                rel = {"kind": "inherited_by", "from_model": other, "to_model": model, "source": "_inherit"}
                if seed_mode or other in requested_set:
                    relationships.append(rel)
                add_external("inheritance_child", other, "_inherit", "model inheriting selected model")
                add_suggestion(other, "model inheriting seed", "_inherit", 80)
            for dst, data in self.edges_out(mid, kind=EDGE_KINDS_DELEGATES):
                other = dst.replace("model::", "")
                via = data.get("via_field")
                rel = {
                    "kind": "delegates_to",
                    "from_model": model,
                    "to_model": other,
                    "via_field": via,
                    "source": "_inherits",
                }
                if seed_mode or other in requested_set:
                    relationships.append(rel)
                add_external("delegation_parent", other, via, "delegation parent")
                add_suggestion(other, "delegation parent", via or "_inherits", 95)
            for src, data in self.edges_in(mid, kind=EDGE_KINDS_DELEGATES):
                other = src.replace("model::", "")
                via = data.get("via_field")
                rel = {
                    "kind": "delegated_by",
                    "from_model": other,
                    "to_model": model,
                    "via_field": via,
                    "source": "_inherits",
                }
                if seed_mode or other in requested_set:
                    relationships.append(rel)
                add_external("delegation_child", other, via, "delegating child")
                add_suggestion(other, "delegating child", via or "_inherits", 85)
            for field_id, _ in self.edges_out(mid, kind=EDGE_KINDS_HAS_FIELD):
                fd = self.node(field_id)
                if not fd or not fd.get("comodel_name"):
                    continue
                other = fd["comodel_name"]
                target_selected = other in requested_set
                target_suggested = other not in requested_set and self.node(self.model_id(other)) is not None
                relation = {
                    "model": model,
                    "field": fd.get("name"),
                    "field_type": fd.get("type"),
                    "target_model": other,
                    "target_selected": target_selected,
                    "target_suggested": target_suggested,
                }
                if seed_mode or target_selected:
                    relations.append(relation)
                if target_selected:
                    relationships.append({
                        "kind": "relates_to",
                        "from_model": model,
                        "to_model": other,
                        "via_field": fd.get("name"),
                        "field_type": fd.get("type"),
                    })
                add_external("relation_comodel", other, fd.get("name"), f"{fd.get('type')} relation")
                add_suggestion(other, f"{fd.get('type')} relation", fd.get("name") or "relation", 60)

        suggested = sorted(suggestions.values(), key=lambda x: (-x["score"], x["model"]))[:8]
        for item in suggested:
            item.pop("score", None)

        high_signal_fields: Dict[str, List[Dict[str, Any]]] = {}
        for item in model_summaries:
            md = item["model"]
            fields: List[Dict[str, Any]] = []
            for flist in item.get("fields_by_module", {}).values():
                for fd in flist:
                    if fd.get("compute") or fd.get("related") or fd.get("inherited") or fd.get("comodel_name"):
                        fields.append({
                            "name": fd.get("name"),
                            "type": fd.get("type"),
                            "module": fd.get("module"),
                            "compute": fd.get("compute"),
                            "related": fd.get("related"),
                            "inherited": bool(fd.get("inherited")),
                            "comodel_name": fd.get("comodel_name"),
                        })
            high_signal_fields[md["name"]] = sorted(
                fields,
                key=lambda f: (0 if f.get("compute") or f.get("related") else 1, f.get("name") or ""),
            )[:12]

        suggested_next_queries: List[str] = []
        if seed_mode and suggested:
            suggested_next_queries.append(
                "odoo-graph context " + " ".join(requested + [s["model"] for s in suggested[:3]]) + " --db <db>"
            )
        for model, fields in high_signal_fields.items():
            for field in fields[:2]:
                suggested_next_queries.append(f"odoo-graph field {model}.{field['name']} --db <db>")
        suggested_next_queries = suggested_next_queries[:6]

        return {
            "mode": "seed" if seed_mode else "explicit_group",
            "result": result,
            "requested_models": requested,
            "selected_models": selected,
            "missing_models": missing,
            "models": model_summaries,
            "relationships": relationships,
            "relations": relations,
            "external_references": external_references[:12],
            "high_signal_fields": high_signal_fields,
            "suggested_context_models": suggested,
            "suggested_next_queries": suggested_next_queries,
            "follow_up_command": suggested_next_queries[0] if seed_mode and suggested_next_queries else None,
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
            f"Dump not found at {layout.out_dir}. Expected nodes.jsonl and edges.jsonl. "
            "Run `odoo-graph dump -d <db>` to create or refresh this cache, "
            "or pass --out-dir/--db for an existing dump."
        )
    return OdooGraph(layout)
