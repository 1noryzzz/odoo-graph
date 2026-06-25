Telemetry Report
================
gap seconds: 60
invocations: 27
first invocation: 2026-05-29T16:55:16.205Z
last invocation: 2026-06-25T03:35:33.835Z
sessions: 6
calls/session avg: 4.50
calls/session p50/p90/p95: 2.0 / 5 / 16

Client frequency:
  local: 21
  codex: 6

Command frequency:
  model: 19
  dump: 4
  field: 1
  module: 1
  impact: 1
  overrides: 1

Format usage:
  human: 21 (failures=2)
  json: 5 (failures=0)
  graphviz: 1 (failures=1)

Follow-up:
  overall: 21
  same target: 2
  different target: 19

Expansion:
  depth escalation: 0
  path expansion: 0
  empty result expansion: 0

Path fan-out:
  groups: 0

Batch exploration:
  multi-model sessions: 2
  multi-field sessions: 0

Top targets:
  dump <none>: 4 (failures=1)
  model ifs.gar.entry.merchant: 2 (failures=1)
  model ifs.gar.invite.mixin: 2 (failures=0)
  model ifs.gar.sub.loan.account: 2 (failures=1)
  model res.partner: 2 (failures=0)
  field ifs.gar.entry.supplier.vat: 1 (failures=0)
  model ifs.gar.entry.supplier: 1 (failures=0)
  module ifs_gar_entry: 1 (failures=0)
  impact res.partner.vat: 1 (failures=0)
  overrides res.users.write: 1 (failures=0)

Top sessions:
  local:0d32fcf02b56:gap60:16:7: 16 calls [local]
    dump -> dump -> model -> model -> model -> model -> model -> model -> model -> model -> model -> model -> model -> model -> model -> model
  019e7426-c3e7-7993-9207-7bdcb901d127:gap60:5:1: 5 calls [codex]
    field -> model -> module -> impact -> overrides
  local:0d32fcf02b56:gap60:3:23: 3 calls [local]
    model -> dump -> model
  019e9cf3-c00f-71d2-8708-eadf31eba563:gap60:1:6: 1 calls [codex]
    dump
  local:719e83593e1c:gap60:1:26: 1 calls [local]
    model

Failure details:
  #7 dump None: dump_error (dump_error)
  #9 model ifs.gar.entry.merchant: unexpected_error (NotImplementedError)
    NotImplementedError: graphviz output is not implemented yet. Phase 1 focuses on the human formatter; graphviz will plug into this same dispatch (see formatters.py).
  #23 model ifs.gar.sub.loan.account: unexpected_error (FileNotFoundError)
    FileNotFoundError: Dump not found at /Users/1noryzzz/.cache/odoo-graph/ysb_m2_manual. Run `odoo-graph dump` first.

Graph source load stats:
  /Users/1noryzzz/.cache/odoo-graph/internal-dev: n=16 avg=1173.19ms p50=1165.0ms p90=1391ms
  /Users/1noryzzz/repos/odoo-graph/odoo_graph/sample_data/17-oabay-ceshi: n=5 avg=834.00ms p50=839ms p90=845ms
  /Users/1noryzzz/.cache/odoo-graph/ysb_m2_manual: n=1 avg=897.00ms p50=897ms p90=897ms

CWD usage:
  /Users/1noryzzz/Odoo: 21 (failures=3)
  /Users/1noryzzz/repos/odoo-graph: 6 (failures=0)

DB usage:
  internal-dev: 18 (failures=2)
  <none>: 6 (failures=0)
  ysb_m2_manual: 3 (failures=1)

Out-dir usage:
  <auto>: 22 (failures=3)
  odoo_graph/sample_data/17-oabay-ceshi: 5 (failures=0)

Command sequences:
  local:0d32fcf02b56:gap60:16:7: dump:- -> dump:- -> model:ifs.gar.entry.merchant -> model:ifs.gar.entry.merchant -> model:ifs.gar.invite.mixin -> model:ifs.gar.invite.merchant -> model:ifs.base.company -> model:ifs.gar.entry.mixin -> model:ifs.contract.info -> model:ifs.gar.invite.mixin -> model:ifs.partner.merchant -> model:ifs.partner.details.mixin
    ... +4 more
  019e7426-c3e7-7993-9207-7bdcb901d127:gap60:5:1: field:ifs.gar.entry.supplier.vat -> model:ifs.gar.entry.supplier -> module:ifs_gar_entry -> impact:res.partner.vat -> overrides:res.users.write
  local:0d32fcf02b56:gap60:3:23: model:ifs.gar.sub.loan.account -> dump:- -> model:ifs.gar.sub.loan.account
  019e9cf3-c00f-71d2-8708-eadf31eba563:gap60:1:6: dump:-
  local:719e83593e1c:gap60:1:26: model:res.partner

Load overhead:
  load ms avg/p50/p90: 1083.55 / 1026.0 / 1391
  load/total ratio: 0.64

Gap sensitivity:
  30s: sessions=6 p50=2.0 p90=5
  60s: sessions=6 p50=2.0 p90=5
  120s: sessions=6 p50=2.0 p90=5
