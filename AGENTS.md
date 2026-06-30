# AGENTS.md

This repository is developed in a design-first workflow. For non-trivial work,
move through three phases: feature design, implementation, and release.

## 1. Feature Design

The user will usually start with a product document under `docs/product/` that
contains ideas, questions, rough goals, or observed usage data.

Use that document as the starting point:

- Read the relevant product doc and nearby docs before proposing changes.
- Discuss the problem until the goal, non-goals, success criteria, and tradeoffs
  are clear.
- Turn loose ideas into a concrete design: user-facing behavior, CLI shape,
  storage/schema changes if any, analysis/reporting expectations, and testing
  strategy.
- When real usage data exists, explicitly separate data-backed changes from
  assumptions.
- Keep design docs updated as decisions change. For example, the 1.7 telemetry
  work used `docs/product/1.7-Event_Tracking/telemetry-design.md` as the design
  source and folded real CSV usage observations back into the doc.

Do not jump directly from a rough idea to code for broad feature work. First
make the implementation path decision-complete enough that another engineer or
agent could build it.

## 2. Development

Implementation should follow the accepted design while respecting the existing
project shape.

General rules:

- Inspect existing code and tests first. Prefer local patterns over new
  abstractions.
- Keep changes scoped to the feature. Avoid unrelated cleanup in the same
  commit.
- Use standard-library capabilities when they are enough; this project currently
  keeps runtime dependencies small.
- Preserve existing CLI output behavior unless the feature explicitly changes
  it. Logs belong on stderr; machine-readable command output belongs on stdout.
- Do not commit generated local artifacts such as `.venv/`, `*.egg-info/`,
  `.pytest_cache/`, or build outputs.
- If `uv.lock` changes because the project version or dependency graph changed,
  include it intentionally. Do not include incidental lockfile churn.

Testing expectations:

- Add focused tests for new behavior.
- For CLI features, test both the Python API entrypoint and the command-facing
  behavior where practical.
- For report/analysis code, test derived metrics with small fixture rows rather
  than relying only on large sample data.
- Run the full test suite before handing off:

```bash
uv run python -m pytest -q
```

For the 1.7 telemetry work, the implementation was split into storage,
runtime collection, report analysis, CLI integration, and tests. Use that as a
model for future features that have both runtime behavior and offline analysis.

## 3. Release

Before a versioned release, update public-facing docs and version metadata.

Documentation checklist:

- `README.md`: quick-start and major user-visible commands.
- `docs/guides/usage.md`: detailed usage, options, examples, and caveats.
- `skills/odoo-graph-runtime-probe/SKILL.md`: agent-facing instructions for
  when and how to use the tool.
- `docs/changes/`: release note or change note for the version.
- `docs/changes/README.md`: index entry for the new change note.
- `docs/product/roadmap.md`: move completed phases out of planned work.
- Relevant `docs/product/...` design docs: keep them aligned with the final
  implementation if behavior changed during development.
- Relevant architecture docs, especially `docs/architecture/overview.md`, if
  the implementation changes storage, data flow, or command architecture.
- CI workflows, if file paths, fixtures, commands, or packaging behavior changed.

Version checklist:

- Update `pyproject.toml` `[project].version`.
- Run `uv sync` or `uv run ...` as needed so editable project metadata and
  `uv.lock` stay consistent.
- Confirm `uv.lock` shows the project package with the same version as
  `pyproject.toml`.
- Run the full test suite after the version change.

Release notes should be practical and user-facing:

- What changed.
- How to use it.
- Compatibility notes.
- Any behavior intentionally excluded from the feature.

For example, the 1.7.0 release note lives at
`docs/changes/1.7-event-tracking.md` and documents the telemetry commands,
local SQLite path, opt-out controls, and compatibility details.

## Cursor Cloud specific instructions

`odoo-graph` is a pure-Python CLI (only runtime dep is `networkx`); there is no
web/GUI service to run. The startup update script runs `uv sync --extra dev`,
which provisions `.venv/` with the editable package plus test deps. `uv` is
already installed in the VM image at `~/.local/bin` (on PATH for login and
non-login shells).

- Run anything through `uv run ...` (e.g. `uv run odoo-graph ...`,
  `uv run python -m pytest -q`). Standard commands are in `README.md`.
- The `dump` subcommand is the only part that needs external services (an Odoo
  17 source tree + PostgreSQL + an initialized DB) and is NOT set up here. All
  other (query/analysis) subcommands work fully offline.
- For offline testing/demo of query commands, point at the committed fixture
  dump with `--out-dir odoo_graph/sample_data/17-oabay-ceshi` instead of `--db`
  (which would resolve to the absent `~/.cache/odoo-graph/<db>/`). The same
  fixture backs the CI `fixture-smoke` job.
- Telemetry writes to `~/.cache/odoo-graph/telemetry.sqlite3` by default; set
  `ODOO_GRAPH_TELEMETRY_DB` or pass `--no-telemetry` to avoid touching it.
