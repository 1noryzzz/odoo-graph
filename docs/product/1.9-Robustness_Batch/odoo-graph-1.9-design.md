# 1.9 Robustness and Batch Primitives Design

Implementation status: 1.9.1 is implemented; 1.9.2 remains planned.

## Background

The 1.8 release introduced the `context` command to reduce repeated model-only exploration observed in the 1.7 telemetry baseline.

The 2026-08-31 telemetry follow-up showed that the dominant workload had changed:

- `context` appeared only once and failed because one model in an explicit group was missing.
- `model` usage fell sharply, but this was not caused by `context`.
- The dominant query pattern became repeated `overrides` and `field` calls.
- The largest business investigation sessions contained 10–18 consecutive queries against related wizard models, methods, and fields.
- On the main M3 workload, the same graph was loaded repeatedly; graph loading represented most of the total query time.
- Dump failures were caused by incorrect `--odoo-path` guesses rather than missing cache data.

At the same time, recent `unified-production` development clarified the actual role of `odoo-graph`.

The tool is primarily used to answer:

> After all installed addons are loaded, what is the final semantic state of the Odoo registry?

Typical investigations include:

- final field lineage after `_inherit` / `_inherits`;
- whether a field is local, inherited, delegated, computed, related, writable, or physically stored;
- the final override chain of a business method;
- whether an AbstractModel, facade, resolver, hook, or extension is actually present in the runtime registry;
- whether a code change has altered the effective registry semantics of the target database.

This positions `odoo-graph` as a **registry semantic probe**, not as a replacement for source search, SQL, runtime tests, or general Python call-graph analysis.

The 1.9 iteration therefore focuses on two immediate needs supported by telemetry:

1. make existing exploration commands more robust and agent-friendly;
2. reduce repetitive single-symbol query bursts without prematurely introducing a larger workflow-level command.

The release is split into two small increments:

- **1.9.1 — Robustness**
- **1.9.2 — Batch Primitives**

---

# 1.9.1 — Robustness

## Goals

1. Make `context` fail open for partially valid explicit model groups.
2. Make missing or mistyped model names actionable instead of turning the whole query into `not_found`.
3. Reduce `dump --odoo-path` trial-and-error in common repository layouts.
4. Preserve the current CLI-oriented architecture and query semantics.
5. Improve reliability for coding agents without adding large new discovery behavior.
6. Keep the product aligned with the registry-semantic-probe boundary.

## Non-Goals

- Do not broaden seed discovery in `context`.
- Do not automatically traverse large relation graphs.
- Do not add a daemon, MCP server, or persistent in-memory graph cache in 1.9.1.
- Do not add registry snapshot diffing yet.
- Do not add physical SQL column verification yet.
- Do not make `odoo-graph` execute business operations or replace Odoo shell / SQL / tests.
- Do not change the existing semantics of `model`, `field`, `impact`, `path`, or `overrides`.

## 1.9.1A — `context` Partial Success

### Problem

Current explicit group behavior is effectively transactional:

```bash
odoo-graph context model.a model.b model.c --db target
```

If any selected model does not exist, the entire command may return `not_found`.

The only observed 1.8 `context` invocation failed in exactly this way. The agent did not correct the model name and retry; it abandoned the command.

For an agent-facing exploration command, this behavior is too brittle.

### Principle

Exploration commands should prefer:

```text
80% resolved + explicit missing items
```

over:

```text
one missing item -> zero result
```

This does not apply to commands where partial output would be unsafe or misleading, such as dump generation.

### Proposed Behavior

For explicit group mode:

```bash
odoo-graph context model.a model.b missing.model model.d --db target
```

return the valid subset and a separate missing section.

Human output:

```text
Context  mode=explicit_group

Resolved models:
  model.a
  model.b
  model.d

Missing models:
  missing.model
    suggestions:
      maybe.model
      missing.model.line

Relations:
  ...

Suggested next queries:
  ...

Result:
  partial
```

JSON output:

```json
{
  "mode": "explicit_group",
  "result": "partial",
  "requested_models": [
    "model.a",
    "model.b",
    "missing.model",
    "model.d"
  ],
  "selected_models": [
    "model.a",
    "model.b",
    "model.d"
  ],
  "missing_models": [
    {
      "name": "missing.model",
      "suggestions": []
    }
  ]
}
```

### Result Semantics

Recommended result states:

- `success`
- `partial`
- `not_found`

Rules:

- all requested models resolved → `success`
- some resolved, some missing → `partial`
- none resolved → `not_found`

CLI exit-code behavior should remain simple:

- `success` → `0`
- `partial` → `0`
- `not_found` → non-zero

Rationale: a partial exploration result is usable output, not command failure.

### Missing-Model Suggestions

Suggestions should remain conservative.

Possible sources:

1. exact suffix / prefix similarity;
2. nearby registry model names;
3. normalized punctuation differences;
4. models already connected to resolved members of the same context group.

Do not perform broad automatic expansion.

Cap suggestions per missing model.

Suggested default: 3.

## 1.9.1B — Dump Path Resolution

### Problem

Recent telemetry showed multiple zero-duration `dump_error` calls caused by incorrect `--odoo-path` guesses:

```text
./odoo-17.0
./odoo
```

while the working path for the current repository layout was:

```text
.
```

This is not a registry problem. It is command setup friction.

### Goal

Make common repository layouts work with less agent-side guessing.

### CLI Resolution Contract

This requires a parser-level behavior change.

Current behavior defaults `--odoo-path` to `$ODOO_PATH` or `./odoo-17.0`. Under 1.9.1 this must change:

- CLI default becomes **unset**.
- `$ODOO_PATH` is treated as an explicit source, with the same precedence as a supplied CLI value.
- Only when neither CLI nor `$ODOO_PATH` provides a value should candidate probing run.

Resolution order:

1. explicit `--odoo-path`;
2. `$ODOO_PATH`;
3. deterministic cwd-relative probing.

For omitted path, probe in this order and use the **first** candidate containing a valid `odoo-bin`:

```text
.
./odoo
./odoo-17.0
../odoo
../odoo-17.0
```

`.` intentionally comes first because this matches the observed `unified-production` repository layout.

The candidate set should remain intentionally small and deterministic.

### Validation

A candidate is valid if the expected Odoo launcher can be resolved, for example:

```text
<candidate>/odoo-bin
```

Do not recursively scan large directory trees.

### Explicit Invalid Path Behavior

An invalid explicit `--odoo-path` or `$ODOO_PATH` must not silently fall through to automatic probing.

Instead:

1. report the invalid explicit path;
2. show the small candidate set that was checked for diagnostics;
3. if a valid cwd-relative candidate exists, print a copyable corrected command.

### Documentation / Skill Compatibility

The runtime-probe skill, README, usage guide, and examples currently showing:

```bash
--odoo-path ./odoo-17.0
```

must be updated in the same release.

Default examples should prefer omitting `--odoo-path` when automatic discovery is appropriate. Explicit-path examples should be used only when demonstrating override behavior.

This is part of the 1.9.1 change, not follow-up documentation work.

### Human Error Output

Example:

```text
Unable to resolve Odoo source path.

cwd:
  /Users/.../Odoo-unified-production

Checked:
  .
  ./odoo
  ./odoo-17.0

Found:
  ./odoo-bin

Suggested command:
  odoo-graph dump -c odoo.conf -d unified-production-m3 --odoo-path .
```

If a valid candidate is detected automatically, print the resolved path in verbose or diagnostic output, but keep normal output compact.

## 1.9.1C — Cache Provenance: Minimal Groundwork

Recent usage repeatedly raised a second reliability issue:

> an old graph cache must not be treated as evidence about the current codebase.

Full cache provenance / freshness design is larger than the immediate P0 scope, but 1.9.1 should prepare for it.

### Minimal Requirement

Ensure each dump metadata record can expose, where available:

- database name;
- dump generation timestamp;
- Odoo source path;
- current working directory;
- `odoo-graph` version;
- model / field / override counts.

If Git metadata is already cheaply available from the source directory, optionally include:

- repository root;
- current commit SHA;
- dirty flag.

This metadata is observational only in 1.9.1.

Do not yet implement automatic stale-cache rejection.

### Query Output

Normal query human / JSON payloads must **not** print provenance by default.

`meta.json` already contains database, Odoo path, addons, summary, and resolve metadata. 1.9.1 only needs to extend it with:

- `generated_at`;
- `cwd`;
- `package_version`.

Git metadata is optional best-effort enrichment:

- repository root;
- commit SHA;
- dirty flag.

Failure to resolve Git metadata must never fail a dump.

The same provenance may be copied into telemetry `extra_json` where useful for later freshness analysis.

1.9.1 does **not** reject stale caches automatically.

## 1.9.1 Telemetry Changes

Add enough telemetry to distinguish robustness outcomes.

For `context`:

- requested model count;
- resolved model count;
- missing model count;
- semantic result state in `result_summary_json.result`: `success` / `partial` / `not_found`.

Telemetry status compatibility is locked as follows:

- CLI `partial` exits `0`;
- telemetry `result_status` remains `success_non_empty` for usable partial output;
- `partial` is **not** introduced as a new top-level `result_status`;
- `result_summary_json` carries:
  - `result`;
  - `requested`;
  - `resolved`;
  - `missing`.

This preserves existing telemetry report semantics while retaining the more precise command-level result.

For `dump`:

- explicit vs inferred `odoo_path`;
- resolved path;
- path resolution failure reason.

Do not record large payload contents.

## 1.9.1 Success Metrics

After release:

1. explicit multi-model `context` no longer drops all useful output because of one missing model;
2. `context` partial results are followed by productive queries more often than immediate abandonment;
3. dump path retries decrease;
4. repeated zero-duration `dump_error` caused by path guessing approach zero;
5. no meaningful regression in existing command output or latency.

---

# 1.9.2 — Batch Primitives

## Background

The strongest 1.8 telemetry pattern is repeated single-symbol investigation:

- `overrides -> overrides` is the dominant command transition;
- `field -> field` is the second major repeated transition;
- the same fields are often queried across related models;
- related methods are queried across multiple wizard / facade implementation models;
- graph load cost is paid repeatedly for queries that conceptually belong to one investigation.

This is not primarily a model discovery problem.

The agent already knows the symbols it wants to inspect. The CLI forces it to query them one by one.

## Goals

1. Allow multiple field targets in one `field` invocation.
2. Allow multiple method targets in one `overrides` invocation.
3. Reuse one graph load for all targets in a batch.
4. Preserve existing single-target behavior.
5. Return independent per-target results so one missing symbol does not discard the rest.
6. Keep the command surface primitive and composable.
7. Collect telemetry that shows whether batch queries materially compress business investigation sessions.

## Non-Goals

- Do not introduce a generic workflow DSL.
- Do not add a heterogeneous `inspect` command in 1.9.2.
- Do not automatically infer the full set of relevant fields or methods.
- Do not merge `field`, `overrides`, `impact`, `path`, and `model` into one command.
- Do not add method-body AST analysis.
- Do not add signature / `super()` correctness checks yet.
- Do not replace Phase 2 persistent caching; batch queries only reduce the number of loads.

---

## 1.9.2A — Batch `field`

### Proposed CLI

Existing:

```bash
odoo-graph field model.a.field_x --db target
```

New:

```bash
odoo-graph field \
  model.a.field_x \
  model.a.field_y \
  model.b.field_x \
  model.b.field_y \
  --db target
```

No new command is introduced.

Single-target syntax remains unchanged.

### Why Positional Multi-Target

Prefer:

```bash
field model.a.x model.b.x
```

over a specialized syntax such as:

```bash
field x --models model.a,model.b
```

because the positional form:

- supports same-model multi-field;
- supports same-field cross-model;
- supports arbitrary mixed batches;
- is easy for agents to construct;
- avoids introducing additional selection semantics.

A specialized cross-model shorthand may be reconsidered later only if telemetry shows strong repeated demand.

### Human Output

```text
Field batch  targets=4

model.a.field_x
  status: found
  type: many2one
  module: module_a
  ...

model.a.field_y
  status: found
  ...

model.b.field_x
  status: found
  ...

model.b.field_y
  status: not_found
  suggestions:
    model.b.field_z

Summary:
  found: 3
  missing: 1
```

### JSON Compatibility Contract

Single-target output is frozen for backward compatibility:

```bash
odoo-graph field model.a.field_x --db target -f json
```

must keep the existing single-target payload and existing `kind=field` formatting behavior.

Only `n >= 2` uses the batch envelope.

Human output follows the same rule: a one-target call must not render `Field batch targets=1`.

For `n >= 2`, JSON output is:

```json
{
  "kind": "field_batch",
  "targets": [
    {
      "target": "model.a.field_x",
      "status": "found",
      "field": {},
      "analysis": {},
      "upstream": [],
      "downstream": []
    },
    {
      "target": "model.b.field_y",
      "status": "not_found",
      "suggestions": []
    }
  ],
  "summary": {
    "requested": 2,
    "found": 1,
    "missing": 1
  }
}
```

A found batch item must embed the current single-target semantic payload (`field`, `analysis`, `upstream`, `downstream`). Do not invent a compacted-only subset in 1.9.2. `status=found` means the field exists in the registry; empty lineage is still `found`, not `not_found`.

### Failure Semantics

Batch `field` should be fail-open:

- some found → exit `0`;
- none found → non-zero.

---

## 1.9.2B — Batch `overrides`

### Proposed CLI

Existing:

```bash
odoo-graph overrides model.a.action_confirm --db target
```

New:

```bash
odoo-graph overrides \
  model.a.action_confirm \
  model.b.action_confirm \
  model.c.confirm_merchant \
  --db target
```

### Human Output

```text
Override batch  targets=3

model.a.action_confirm
  status: found
  chain:
    module_a
    module_b

model.b.action_confirm
  status: found
  chain:
    module_c
    module_d
    module_e

model.c.confirm_merchant
  status: not_found

Summary:
  found: 2
  missing: 1
```

### JSON Compatibility Contract

Single-target output is frozen for backward compatibility:

```bash
odoo-graph overrides model.a.action_confirm --db target -f json
```

must keep the existing single-target payload and existing `kind=overrides` formatting behavior.

Only `n >= 2` uses the batch envelope.

Human output follows the same rule: a one-target call must not render `Override batch targets=1`.

For `n >= 2`, JSON output is:

```json
{
  "kind": "overrides_batch",
  "targets": [
    {
      "target": "model.a.action_confirm",
      "status": "found"
    },
    {
      "target": "model.c.confirm_merchant",
      "status": "not_found",
      "suggestions": []
    }
  ],
  "summary": {
    "requested": 2,
    "found": 1,
    "missing": 1
  }
}
```

A found batch item must embed the current single-target `overrides` payload. Do not invent a compacted-only subset in 1.9.2.

### Ordering

Preserve user-supplied target order.

Within each target, preserve the current override ordering semantics.

---

## Shared Batch Behavior

### Batch Telemetry Contract

For batch `field` and `overrides`:

- `target_raw` is a comma-joined list of the requested targets, matching the existing `context` convention;
- `result_summary_json` contains:
  - `result`: `success` / `partial` / `not_found`;
  - `requested`;
  - `found`;
  - `missing`;
- partial batches exit `0`;
- telemetry `result_status` remains `success_non_empty` when at least one usable target result is returned;
- all-missing batches remain `not_found`.

The telemetry contract must distinguish one invocation with 10 targets from 10 single-target invocations.

### Graph Loading

The graph must be loaded once per command invocation.

Pseudo-flow:

```text
parse all targets
        ↓
load graph once
        ↓
query target 1
query target 2
query target 3
        ↓
format aggregate result
```

This is an important performance property, not merely an implementation detail.

### Per-Target Isolation

Each target is independent.

One `not_found` item must not invalidate other targets.

### Batch Size

Use a **hard limit of 50 targets**.

Validation must happen before graph loading.

If the request exceeds 50 targets:

- return a usage error;
- do not load the graph;
- do not partially execute the first 50 items.

A hard limit is intentionally preferred over a soft limit because it produces deterministic behavior and is visible in telemetry.

### Output Compactness

Batch output is primarily intended for coding agents.

Avoid repeating large headers or global metadata for each item.

The human formatter should optimize for:

- target separation;
- dense semantic evidence;
- low token overhead.

---

# 1.9 Product Principles

The 1.9 work should follow these principles.

## 1. Registry Semantics First

`odoo-graph` answers questions about the final loaded Odoo registry.

It should not attempt to become:

- a full Python call graph engine;
- a SQL truth source;
- a business workflow executor;
- an integration test runner.

## 2. Partial Evidence Is Better Than Total Failure

For exploratory commands:

```text
valid results + explicit missing items
```

is preferable to discarding valid evidence.

## 3. Batch Known Symbols Before Inventing More Discovery

Current telemetry shows that agents frequently already know the target symbols.

The first optimization should therefore be to query those symbols efficiently.

## 4. One Investigation Should Not Pay Repeated Load Tax

Batch commands should reuse a single graph load.

Persistent caching remains a Phase 2 concern.

## 5. Human Output Remains First-Class

Recent telemetry overwhelmingly uses human output.

`-f human` should remain compact and agent-readable.

`-f json` should remain stable and structured for machine handoff, future MCP use, and integration with tools such as CodeGraph.

---

# Deferred Directions After 1.9

The following directions are important but intentionally deferred until 1.9 telemetry is available.

## Registry Snapshot Diff

Compare two dumps to answer questions such as:

- which models appeared or disappeared;
- which fields changed ownership or semantics;
- which override chains changed;
- whether a migration changed the effective registry contract.

This is especially relevant when moving an existing business implementation behind a new facade.

## Cache Provenance / Freshness Enforcement

Possible future behavior:

```text
dump generated from:
  db
  source commit
  dirty state
  timestamp
```

Queries may later warn when the cache does not match the current source checkout.

## Physical Storage Mapping

Expose a clear distinction between:

- registry-visible field;
- inherited field;
- delegated field;
- computed non-stored field;
- local stored field;
- expected physical table / column.

Any SQL-facing feature must still be explicit about the boundary between registry-derived expectation and database-verified schema.

## CodeGraph Handoff

Structured `impact` / `path` JSON may become a handoff contract:

```text
odoo-graph
  registry field / model evidence
        ↓
CodeGraph
  Python method / controller / execution path
```

This should remain a tool boundary rather than merging the two systems.

## Heterogeneous Investigation Command

If post-1.9 telemetry still shows mixed bursts such as:

```text
field x N
overrides x N
model x N
```

around the same business task, consider a higher-level primitive such as:

```text
inspect
```

or a broader evolution of `context`.

It could accept a known set of models, fields, and methods and return one compact registry investigation package.

Do not implement this until batch primitives have been measured.

---

# Locked Compatibility Decisions

The following decisions are implementation contracts for 1.9 and should not be re-decided during coding:

1. `--odoo-path` parser default is unset; `$ODOO_PATH` is explicit; probing only runs when both are absent.
2. Auto-discovery uses the documented deterministic order and the first valid `odoo-bin`.
3. Single-target `field` / `overrides` human and JSON output remain backward compatible.
4. Batch envelopes exist only for `n >= 2`.
5. Found batch items embed the current single-target payload; empty lineage is `found`.
6. Partial usable output exits `0`.
7. Telemetry top-level `result_status` does not gain a new `partial` value.
8. Semantic `success` / `partial` / `not_found` lives in `result_summary_json.result`.
9. Batch `target_raw` is comma-joined and summary includes requested/found/missing counts.
10. Batch target count has a hard pre-load limit of 50.
11. 1.9.1 provenance extends `meta.json` minimally and is not printed in normal query output.
12. Git SHA / dirty metadata is best-effort only.
13. No automatic stale-cache rejection is introduced in 1.9.

# Implementation Order

## 1.9.1

1. change `context` explicit-group resolution to partial success;
2. add missing-model result metadata and conservative suggestions;
3. improve `dump --odoo-path` resolution and diagnostics;
4. enrich minimal dump provenance metadata;
5. extend telemetry;
6. add regression tests.

## 1.9.2

1. generalize `field` parser to accept multiple targets;
2. implement one-load batch execution;
3. add aggregate human / JSON formatting;
4. generalize `overrides` parser to accept multiple targets;
5. add independent per-target failure handling;
6. extend telemetry with batch size and result counts;
7. add compatibility and performance tests.

---

# Telemetry Acceptance Plan

After 1.9.2 has been used in real development, compare against the 2026-08-31 baseline.

Key metrics:

- `field -> field` transition count;
- `overrides -> overrides` transition count;
- average targets per `field` invocation;
- average targets per `overrides` invocation;
- calls per active business investigation session;
- graph loads per session;
- load time / total query time ratio;
- partial-result frequency;
- retry frequency after `not_found`;
- whether new mixed query bursts emerge.

The main success criterion is not simply fewer CLI invocations.

The intended outcome is:

> one agent investigation should require fewer repeated graph loads and less manual assembly of registry evidence, while preserving explicit, trustworthy semantic boundaries.

---

# Version Summary

## 1.9.1 — Robustness

Focus:

- `context` fail-open;
- actionable missing-model handling;
- dump path resolution;
- minimal provenance groundwork;
- reliability telemetry.

## 1.9.2 — Batch Primitives

Focus:

- multi-target `field`;
- multi-target `overrides`;
- one graph load per batch;
- partial per-target results;
- telemetry to validate whether bursts are actually compressed.

The broader product direction remains:

> `odoo-graph` is a runtime registry semantic probe for coding agents and developers.

Future expansion should improve confidence, comparison, and interoperability around that role rather than turn the tool into a general-purpose Odoo execution engine.
