"""odoo_graph — Odoo registry runtime-probe + dependency graph analyzer.

Public surface:
    - dump()          run Odoo and emit nodes/edges JSONL
    - load_graph()    load a previous dump as networkx.MultiDiGraph
    - queries         high-level analysis helpers

CLI entry point:
    odoo-graph dump|field|model|module|impact|overrides ...
"""
from __future__ import annotations

__version__ = "0.1.0"

from .graph import OdooGraph, load_graph

__all__ = ["OdooGraph", "load_graph", "__version__"]
