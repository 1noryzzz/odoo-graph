"""Snapshot-style assertions for the CI smoke run (base+mail minimal DB).

This is intentionally loose — exact counts will drift when Odoo ships minor
updates. We assert ranges / presence, not specific numbers. If a check fails
here, something meaningful regressed in the probe output.
"""
from __future__ import annotations

import json
import sys


REQUIRED_KEYS = {
    "out_dir", "summary", "resolve",
}
SUMMARY_MIN = {
    # (key, minimum) — set lower bounds so Odoo 17 patch releases don't break CI
    "models": 60,            # base+mail alone defines ~90 in Odoo 17
    "fields": 1000,
    "fields_computed": 200,
    "fields_related": 100,
    "fields_inherited_delegate": 0,  # base+mail has almost none, just sanity
    "methods_with_overrides": 200,
    "edges_depends_field": 400,
    "edges_module_depends": 2,
}


def _fail(msg: str) -> None:
    print(f"SNAPSHOT ASSERT FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


def main(path: str) -> int:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    for k in REQUIRED_KEYS:
        if k not in doc:
            _fail(f"missing key '{k}' in dump result: {list(doc)}")

    s = doc["summary"]
    for k, lo in SUMMARY_MIN.items():
        if s.get(k, 0) < lo:
            _fail(f"summary.{k}={s.get(k)} < expected minimum {lo}")

    r = doc["resolve"]
    if r["resolved"] < 100:
        _fail(f"resolve.resolved={r['resolved']} unexpectedly low")
    # A few abstract mixin paths will always be unresolved (avatar.mixin.name etc.)
    if r["unresolved"] > 50:
        _fail(f"resolve.unresolved={r['unresolved']} unusually high")

    print(f"snapshot OK: {s['models']} models / {s['fields']} fields / "
          f"{r['resolved']} resolved / {r['unresolved']} unresolved")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m odoo_graph.tests.snapshot_asserts <dump.json>",
              file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
