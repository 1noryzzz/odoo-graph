# 1.8 Context Command Design

## Background

The 1.7 telemetry report showed that agent exploration is currently dominated by repeated single-model queries:

- 27 total tracked invocations across 6 sessions.
- `model` was used 19 times, far more than any other command.
- The largest session was `dump -> dump -> model x14`.
- Follow-up calls were mostly different targets: 19 different-target follow-ups vs 2 same-target follow-ups.
- Path fan-out was not present in the 2026-06-25 report.

This points to a specific product gap: agents are not primarily retrying the same query or increasing depth. They are manually assembling a local model context by calling `model` repeatedly.

## Goals

1. Add a seed-first model exploration command that lets an agent start from one known model and discover the next useful context models.
2. Make Odoo inheritance semantics explicit in the output, especially:
   - same-model extension through `_inherit = "same.model"`;
   - classic/multiple model inheritance through `_inherit = ["a", "b"]`;
   - delegation through `_inherits = {"parent.model": "field_id"}`;
   - abstract and transient model flags.
3. Keep explicit multi-model context for cases where the agent already knows the model set.
4. Reduce repeated single-target `model` calls in agent workflows.
5. Keep missing cache and dump errors easier to act on with clearer messages and a re-dump hint.

## Non-Goals

- Do not build an MCP server, daemon, or persistent graph cache in 1.8.
- Do not add cache management commands such as `cache list`, `cache status`, or `doctor`.
- Do not add path fan-out commands in 1.8, because the current report did not show path fan-out.
- Do not change the existing single-target `model` command semantics.
- Do not attempt broad automatic prefix expansion in the first version.
- Do not require the user or agent to know the full model set before using `context`.

## Proposed Command

Add a new command:

```bash
odoo-graph context <model> [<model> ...] --db <db>
```

Examples:

```bash
odoo-graph context ifs.gar.entry.merchant --db internal-dev
odoo-graph context ifs.gar.entry.merchant ifs.gar.invite.merchant --db internal-dev
odoo-graph context res.partner res.users res.company --db odoo_demo -f json
```

The command accepts model names only. Field/path exploration remains handled by the existing `field`, `impact`, and `path` commands.

`context` has two modes:

1. **Seed discovery**: `context <model>` starts from one known model and returns the directly relevant inheritance, delegation, and relation candidates.
2. **Explicit group context**: `context <model> <model> ...` explains the relationship between a known model set.

## Product Behavior

`context` answers:

> Starting from this model, or this explicit group of models, what is the final runtime registry relationship and what context should I inspect next?

It should return:

1. A compact identity summary for each selected model.
2. Direct inheritance and delegation parents for the seed or selected models.
3. Relation fields between selected models.
4. External parent/delegate/comodel references that are important but were not selected.
5. High-signal fields grouped by model.
6. `suggested_context_models` for the next wider `context` call.
7. A small list of suggested next queries.

In seed discovery mode, inheritance and delegation neighbors are first-class output. Relation comodels are candidates, not automatically expanded without limit.

## Odoo Semantics

### Same-Model Extension

Odoo modules frequently extend an existing model with:

```python
_inherit = "res.partner"
```

At runtime this is not a separate parent model edge. The current dump already skips self-inheritance edges. `context` should represent same-model extension through:

- `model.contributing_modules`;
- fields grouped by module;
- module extension edges where available.

The output should not invent a `res.partner -> res.partner` inheritance edge.

### Classic and Multiple Model Inheritance

When `_inherit` points to one or more different models, `context` should use existing `MODEL_INHERITS_MODEL` edges.

For each edge, include:

- child model;
- parent model;
- `via_module` when available;
- whether the parent model is selected;
- parent model flags: `abstract`, `transient`.

This is important for mixin-heavy Odoo modules, where many useful parents are abstract models.

### Delegation Inheritance

When `_inherits` maps parent models to foreign-key fields, `context` should use existing `MODEL_DELEGATES_TO_MODEL` edges.

For each delegation, include:

- child model;
- parent model;
- `via_field`;
- whether the parent model is selected;
- the delegation chain already available from `model_summary()`.

Delegation must be distinct from classic inheritance because it affects field ownership, SQL columns, and write semantics.

### Abstract and Transient Models

Every model entry should explicitly show:

- `abstract`;
- `transient`;
- table name;
- original module;
- contributing modules.

Human output can render a compact `kind`:

- `normal`;
- `abstract`;
- `transient`;
- `abstract+transient` if both flags are true.

JSON output should keep the booleans as separate fields.

## Human Output Shape

Suggested first version:

```text
Context  seed=ifs.gar.entry.merchant

Models:
  ifs.gar.entry.merchant
    kind: normal
    table: ifs_gar_entry_merchant
    original module: ifs_gar_entry
    contributing: ifs_gar_entry, ifs_gar_invite
    flags: abstract=false transient=false

Inheritance:
  ifs.gar.entry.merchant inherits:
    - ifs.gar.entry.mixin via module ifs_gar_entry [abstract=true transient=false]

Delegation:
  ifs.gar.entry.merchant delegates:
    - ifs.gar.invite.merchant via invite_id [selected=false suggested=true]
      chain: ifs.gar.entry.merchant --invite_id--> ifs.gar.invite.merchant

Relation candidates:
  ifs.gar.entry.merchant.invite_id -> ifs.gar.invite.merchant [many2one, suggested]
  ifs.gar.entry.merchant.merchant_id -> ifs.partner.merchant [many2one]

High-signal fields:
  ifs.gar.entry.merchant:
    relation: invite_id, merchant_id
    related: vat, legal_name
    delegated: vat
    computed: display_name
    multi-module: name

External related models:
  res.partner [normal]
  mail.thread [abstract]

Suggested context models:
  ifs.gar.invite.merchant  reason=delegation via invite_id
  ifs.gar.entry.mixin      reason=abstract inherited parent
  ifs.partner.merchant     reason=relation field merchant_id

Suggested next queries:
  odoo-graph context ifs.gar.entry.merchant ifs.gar.invite.merchant --db <db>
  odoo-graph field ifs.gar.entry.merchant.vat --db <db>
  odoo-graph path ifs.gar.entry.merchant.vat res.partner.vat --db <db>
```

The exact field names in examples are illustrative. The implementation should only render data that exists in the active dump.

## JSON Output Shape

The JSON contract should be stable enough for agents to consume:

```json
{
  "mode": "seed",
  "seed_model": "ifs.gar.entry.merchant",
  "selected_models": ["ifs.gar.entry.merchant"],
  "models": [
    {
      "name": "ifs.gar.entry.merchant",
      "table": "ifs_gar_entry_merchant",
      "original_module": "ifs_gar_entry",
      "contributing_modules": ["ifs_gar_entry"],
      "abstract": false,
      "transient": false
    }
  ],
  "inheritance": {
    "same_model_extensions": [],
    "model_inherits": [],
    "delegates": []
  },
  "relations": [],
  "high_signal_fields": {},
  "external_related_models": [],
  "suggested_context_models": [],
  "suggested_next_queries": []
}
```

For explicit group mode, use:

```json
{
  "mode": "explicit_group",
  "seed_model": null,
  "selected_models": [
    "ifs.gar.entry.merchant",
    "ifs.gar.invite.merchant"
  ]
}
```

### `inheritance.same_model_extensions`

Each item should describe one selected model's module-level extension evidence:

```json
{
  "model": "res.partner",
  "contributing_modules": ["base", "mail", "contacts"],
  "field_modules": ["base", "mail"]
}
```

### `inheritance.model_inherits`

Each item should describe a classic inheritance edge:

```json
{
  "child": "ifs.gar.entry.merchant",
  "parent": "ifs.gar.entry.mixin",
  "via_module": "ifs_gar_entry",
  "parent_selected": false,
  "parent_suggested": true,
  "parent_abstract": true,
  "parent_transient": false
}
```

### `inheritance.delegates`

Each item should describe a delegation edge:

```json
{
  "child": "ifs.gar.entry.merchant",
  "parent": "ifs.gar.invite.merchant",
  "via_field": "invite_id",
  "parent_selected": false,
  "parent_suggested": true
}
```

### `relations`

Each item should describe a relation field from a selected model. In explicit group mode, relation targets may also be selected. In seed mode, relation targets are usually candidates.

```json
{
  "from_model": "ifs.gar.entry.merchant",
  "field": "invite_id",
  "field_type": "many2one",
  "to_model": "ifs.gar.invite.merchant",
  "target_selected": false,
  "target_suggested": true
}
```

### `high_signal_fields`

Fields should be grouped by selected model:

```json
{
  "ifs.gar.entry.merchant": {
    "relation": [],
    "computed": [],
    "related": [],
    "delegated": [],
    "multi_module": []
  }
}
```

Each field entry should include enough metadata for an agent to decide whether to run `field` next:

```json
{
  "name": "vat",
  "type": "char",
  "module": "base",
  "modules": ["base", "contacts"],
  "comodel_name": null,
  "compute": null,
  "related": ["partner_id", "vat"],
  "inherited": true,
  "inherited_from_model": "res.partner"
}
```

### `suggested_context_models`

Each item should explain why adding that model to a follow-up `context` call is useful:

```json
{
  "model": "ifs.gar.invite.merchant",
  "reason": "delegation",
  "via": "invite_id",
  "abstract": false,
  "transient": false
}
```

Initial seed-mode ranking:

1. Delegation parents from `_inherits`.
2. Classic inherited parents, especially abstract mixins.
3. Relation comodels from high-signal relation fields.
4. Other relation comodels, capped to avoid broad expansion.

Do not emit more than 8 suggested context models by default.

## Suggested Next Queries

Suggestions should be sparse. They are meant to reduce guesswork, not produce a to-do list.

Initial rules:

- In seed mode, suggest one follow-up `context <seed> <suggested...>` command when useful.
- For delegated or inherited fields, suggest `field <model.field>`.
- If a field has a clear source field, suggest `path <model.field> <source.field>`.
- For external abstract parents, suggest adding that parent to `context` only if it has high relevance.

Do not emit more than 5 suggestions by default.

## Error Message Enhancement

This is intentionally small in 1.8.

### Missing Cache

Current missing-cache errors should be replaced with a clearer message:

```text
Dump cache not found: /Users/.../.cache/odoo-graph/ysb_m2_manual
Resolved from: --db ysb_m2_manual
Missing required files: nodes.jsonl, edges.jsonl

Rebuild the cache:
  odoo-graph dump -c odoo.conf -d ysb_m2_manual --odoo-path ./odoo-17.0
```

If the command used `--out-dir`, say `Resolved from: --out-dir <path>`.

### Dump Error

Dump errors should keep the current stderr tail, but add a concise next step:

```text
Dump failed while running odoo-bin shell for db ysb_m2_manual.
<stderr tail>

After fixing the cause, rebuild the cache:
  odoo-graph dump -c odoo.conf -d ysb_m2_manual --odoo-path ./odoo-17.0
```

No new cache management commands are planned for 1.8.

## Implementation Notes

Recommended shape:

1. Add `OdooGraph.context_summary(models: list[str])`.
2. Treat `len(models) == 1` as seed discovery and `len(models) > 1` as explicit group context.
3. Reuse `model_summary()` where practical, but keep `context` output compact.
4. Add a `cmd_context()` CLI command and a parser entry.
5. Add human/json formatter support for `kind="context"`.
6. Keep `model` unchanged.
7. Add focused tests for:
   - seed discovery from one model;
   - multiple selected models;
   - classic inheritance edge;
   - delegation edge and chain;
   - abstract/transient flags;
   - relation fields between selected models;
   - suggested context models;
   - missing model suggestions;
   - missing cache error text.

## Success Metrics

Use telemetry after 1.8 to check:

- `model` calls per session decrease.
- single-seed `context` calls appear before explicit multi-model `context` calls in exploratory sessions.
- `context` appears in sessions that previously looked like multi-model bursts.
- different-target follow-up count decreases for model exploration tasks.
- missing-cache failures lead to a `dump` retry without manual clarification.

The expected improvement is not that all follow-up disappears. The goal is that one `context` call replaces repetitive model-only context assembly.
