# AGENTS.md

This repository uses a design-first workflow for broad feature changes.
Focused fixes and documentation maintenance do not need to repeat feature
design. Apply release requirements only when the task includes a versioned release.

## 1. Feature Design

The user will usually start with a product document under `docs/product/` that
contains ideas, questions, rough goals, or observed usage data.

Use that document as the starting point:

- Read the relevant product doc and supporting docs needed for the change.
- When the accepted design and task context establish the goal, non-goals,
  success criteria, and tradeoffs, continue implementation. Clarify only unresolved
  decisions that materially affect scope, compatibility, or acceptance.
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
- Complete authorized investigation, implementation, verification, and fixes
  for regressions introduced by this change or required for acceptance within
  the authorized scope. Report unrelated pre-existing issues without fixing them;
  do not stop at a preliminary implementation or investigation handoff.
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
- Run checks appropriate to the affected behavior and complete required checks.
  For documentation-only changes, check the changed wording, references, and diff;
  run code tests only when the change affects executable behavior.
- Once relevant checks pass, broaden or repeat them only for new changes,
  failures, or unresolved concerns. Report validation actually performed and
  material unverified gaps.

### Runtime-probe skill maintenance

Incrementally maintain `skills/odoo-graph-runtime-probe/` when implemented
behavior affects its guidance; do not regenerate it from scratch each release.

- Keep applicability, evidence boundaries, environment/cache constraints, query
  selection, and stopping conditions in `SKILL.md`. Put command examples,
  parameters, and output explanations in `references/cli.md`, linked for on-demand use.
- Ground changes in current implementation, CLI help, and relevant tests.
  Proposals and historical release notes alone do not prove current behavior.
- Avoid fixed command sequences, repeated confirmation, mandatory answer
  templates, and consumer-project-specific paths, databases, or environment settings.
- Update only guidance affected by the change. Verify modified references and
  command descriptions; follow the testing scope and stopping conditions above.

## 3. Release

Before a versioned release, update public-facing docs and version metadata.

Check the following documentation surfaces and update those affected by the release:

- `README.md`: quick-start and major user-visible commands.
- `docs/guides/usage.md`: detailed usage, options, examples, and caveats.
- `skills/odoo-graph-runtime-probe/`: agent-facing instructions and on-demand
  references, following the maintenance rules above. Verify the release archive
  includes the required files and preserves their relative paths so links resolve.
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
- Run the full test suite after the version change: `uv run python -m pytest -q`.

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
web/GUI service to run.

Cloud Agent environment builds run `.cursor/install.sh` (see
`.cursor/environment.json`). That script installs `uv` if it is missing, copies
it to `/usr/local/bin` so agent shells can find it, then runs
`uv sync --extra dev` to provision `.venv/` with the editable package plus test
deps. Do not assume the base image already contains `uv`: Cursor's default
snapshot does not, and agent PATH typically omits `~/.local/bin`.

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
