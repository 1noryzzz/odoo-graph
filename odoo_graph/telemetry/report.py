"""Post-processing and reporting for telemetry invocations."""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from .store import fetch_invocations


SENSITIVITY_GAPS = (30, 60, 120)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * pct)
    return ordered[index]


def _avg(values: Iterable[int | float]) -> float | None:
    vals = list(values)
    if not vals:
        return None
    return sum(vals) / len(vals)


def _field_name(row: dict[str, Any]) -> str | None:
    if row.get("target_field"):
        return row["target_field"]
    raw = row.get("target_raw")
    if not raw or "." not in raw:
        return None
    return raw.rsplit(".", 1)[1]


def _model_name(row: dict[str, Any]) -> str | None:
    if row.get("target_model"):
        return row["target_model"]
    raw = row.get("target_raw")
    if not raw or "." not in raw:
        return raw
    return raw.rsplit(".", 1)[0]


def _prefix(row: dict[str, Any]) -> str | None:
    raw = row.get("target_model") or row.get("target_raw")
    if not raw:
        return None
    parts = raw.split(".")
    if len(parts) < 2:
        return raw
    return ".".join(parts[:2])


def derive_sessions(rows: list[dict[str, Any]], gap_seconds: int) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row.get("codex_thread_id") or "unknown"].append(row)

    sessions: list[dict[str, Any]] = []
    for thread_id, thread_rows in groups.items():
        current: list[dict[str, Any]] = []
        previous_time: datetime | None = None
        for row in sorted(thread_rows, key=lambda r: (r["started_at"], r["id"])):
            started = _parse_time(row["started_at"])
            if (
                previous_time is not None
                and (started - previous_time).total_seconds() > gap_seconds
            ):
                sessions.append(_session(thread_id, gap_seconds, current))
                current = []
            current.append(row)
            previous_time = started
        if current:
            sessions.append(_session(thread_id, gap_seconds, current))
    return sorted(sessions, key=lambda s: s["started_at"])


def _session(thread_id: str, gap_seconds: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "session_key": f"{thread_id}:gap{gap_seconds}:{len(rows)}:{rows[0]['id']}",
        "thread_id": thread_id,
        "gap_seconds": gap_seconds,
        "started_at": rows[0]["started_at"],
        "ended_at": rows[-1].get("ended_at") or rows[-1]["started_at"],
        "rows": rows,
    }


def analyze(rows: list[dict[str, Any]], gap_seconds: int = 60) -> dict[str, Any]:
    sessions = derive_sessions(rows, gap_seconds)
    counts = [len(s["rows"]) for s in sessions]
    flat = [row for s in sessions for row in s["rows"]]
    transitions: Counter[tuple[str, str]] = Counter()
    followups = 0
    same_target_followups = 0
    different_target_followups = 0
    exact_retries = 0
    parameter_retries = 0
    failure_retries = 0
    depth_escalations = 0
    path_expansions = 0
    empty_expansions = 0
    path_fanout_groups: list[dict[str, Any]] = []
    same_field_cross_model_groups: list[dict[str, Any]] = []
    same_model_multi_field_groups: list[dict[str, Any]] = []
    same_prefix_groups: list[dict[str, Any]] = []
    multi_model_sessions = 0
    multi_field_sessions = 0

    for session in sessions:
        rows_in_session = session["rows"]
        if len([r for r in rows_in_session if r["command"] == "model"]) >= 2:
            multi_model_sessions += 1
        if len([r for r in rows_in_session if r["command"] == "field"]) >= 2:
            multi_field_sessions += 1
        seen_exact: set[tuple[Any, ...]] = set()
        by_command_target: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
        by_path_pair: dict[tuple[str | None, str | None], list[dict[str, Any]]] = defaultdict(list)
        path_by_start: dict[str | None, set[str | None]] = defaultdict(set)
        fields_by_model: dict[str | None, set[str | None]] = defaultdict(set)
        models_by_field: dict[str | None, set[str | None]] = defaultdict(set)
        targets_by_prefix: dict[str | None, set[str | None]] = defaultdict(set)

        for idx, row in enumerate(rows_in_session):
            exact_key = (
                row["command"],
                row.get("target_raw"),
                row.get("start_raw"),
                row.get("max_depth"),
                row.get("max_paths"),
                row.get("allow_kinds"),
            )
            if exact_key in seen_exact:
                exact_retries += 1
            seen_exact.add(exact_key)
            by_command_target[(row["command"], row.get("target_raw"))].append(row)
            if row["command"] == "path":
                by_path_pair[(row.get("start_raw"), row.get("target_raw"))].append(row)
                path_by_start[row.get("start_raw")].add(row.get("target_raw"))
            if row["command"] == "field":
                fields_by_model[_model_name(row)].add(_field_name(row))
                models_by_field[_field_name(row)].add(_model_name(row))
            pref = _prefix(row)
            targets_by_prefix[pref].add(row.get("target_raw"))
            if idx == 0:
                continue
            previous = rows_in_session[idx - 1]
            transitions[(previous["command"], row["command"])] += 1
            followups += 1
            if previous.get("target_raw") == row.get("target_raw"):
                same_target_followups += 1
            else:
                different_target_followups += 1
            if not previous.get("success") and row.get("target_raw") == previous.get("target_raw"):
                failure_retries += 1
            if previous.get("empty_result"):
                empty_expansions += 1

        for group_rows in by_command_target.values():
            depths = [r.get("max_depth") for r in group_rows if r.get("max_depth") is not None]
            if len(depths) >= 2 and max(depths) > min(depths):
                depth_escalations += 1
            params = {
                (r.get("max_depth"), r.get("max_paths"), r.get("allow_kinds"))
                for r in group_rows
            }
            if len(group_rows) >= 2 and len(params) >= 2:
                parameter_retries += 1
        for group_rows in by_path_pair.values():
            max_paths = [r.get("max_paths") for r in group_rows if r.get("max_paths") is not None]
            if len(max_paths) >= 2 and max(max_paths) > min(max_paths):
                path_expansions += 1
        for start, targets in path_by_start.items():
            clean_targets = {t for t in targets if t}
            if len(clean_targets) >= 2:
                path_fanout_groups.append({
                    "session_key": session["session_key"],
                    "start_raw": start,
                    "distinct_targets": len(clean_targets),
                })
        for model, fields in fields_by_model.items():
            clean_fields = {f for f in fields if f}
            if model and len(clean_fields) >= 2:
                same_model_multi_field_groups.append({
                    "session_key": session["session_key"],
                    "target_model": model,
                    "distinct_fields": len(clean_fields),
                })
        for field, models in models_by_field.items():
            clean_models = {m for m in models if m}
            if field and len(clean_models) >= 2:
                same_field_cross_model_groups.append({
                    "session_key": session["session_key"],
                    "target_field": field,
                    "distinct_models": len(clean_models),
                })
        for pref, targets in targets_by_prefix.items():
            clean_targets = {t for t in targets if t}
            if pref and len(clean_targets) >= 3:
                same_prefix_groups.append({
                    "session_key": session["session_key"],
                    "prefix": pref,
                    "distinct_targets": len(clean_targets),
                })

    loads = [row["duration_load_ms"] for row in flat if row.get("duration_load_ms") is not None]
    totals = [row["duration_total_ms"] for row in flat if row.get("duration_total_ms") is not None]
    return {
        "gap_seconds": gap_seconds,
        "invocation_count": len(flat),
        "command_frequency": dict(Counter(row["command"] for row in flat).most_common()),
        "session_metrics": {
            "session_count": len(sessions),
            "invocation_count_average": _avg(counts),
            "invocation_count_p50": statistics.median(counts) if counts else None,
            "invocation_count_p90": _percentile(counts, 0.90),
            "invocation_count_p95": _percentile(counts, 0.95),
        },
        "followup": {
            "overall_count": followups,
            "same_target_count": same_target_followups,
            "different_target_count": different_target_followups,
        },
        "retry": {
            "exact_retry_count": exact_retries,
            "parameter_retry_count": parameter_retries,
            "failure_retry_count": failure_retries,
        },
        "expansion": {
            "depth_escalation_count": depth_escalations,
            "path_expansion_count": path_expansions,
            "empty_result_expansion_count": empty_expansions,
        },
        "path_fanout": {
            "group_count": len(path_fanout_groups),
            "groups": sorted(
                path_fanout_groups,
                key=lambda g: g["distinct_targets"],
                reverse=True,
            )[:20],
        },
        "batch_exploration": {
            "multi_model_session_count": multi_model_sessions,
            "multi_field_session_count": multi_field_sessions,
            "same_model_multi_field_groups": sorted(
                same_model_multi_field_groups,
                key=lambda g: g["distinct_fields"],
                reverse=True,
            )[:20],
            "same_field_cross_model_groups": sorted(
                same_field_cross_model_groups,
                key=lambda g: g["distinct_models"],
                reverse=True,
            )[:20],
            "same_prefix_groups": sorted(
                same_prefix_groups,
                key=lambda g: g["distinct_targets"],
                reverse=True,
            )[:20],
        },
        "load_overhead": {
            "load_ms_average": _avg(loads),
            "load_ms_p50": statistics.median(loads) if loads else None,
            "load_ms_p90": _percentile(loads, 0.90),
            "load_to_total_duration_ratio": (
                sum(loads) / sum(totals) if loads and totals and sum(totals) else None
            ),
            "same_graph_repeated_load_count": max(0, len(loads) - len({
                _extra_value(row, "graph_cache_key")
                for row in flat
                if row.get("duration_load_ms") is not None
            })),
        },
        "top_transitions": [
            {"from": src, "to": dst, "count": count}
            for (src, dst), count in transitions.most_common(20)
        ],
    }


def _extra_value(row: dict[str, Any], key: str) -> Any:
    raw = row.get("extra_json")
    if not raw:
        return None
    try:
        return json.loads(raw).get(key)
    except json.JSONDecodeError:
        return None


def build_report(path: str | None = None, gap_seconds: int = 60) -> dict[str, Any]:
    rows = fetch_invocations(path)
    return {
        "selected_gap_seconds": gap_seconds,
        "sensitivity": {
            str(gap): analyze(rows, gap)["session_metrics"]
            for gap in SENSITIVITY_GAPS
        },
        "analysis": analyze(rows, gap_seconds),
    }


def render_report(report: dict[str, Any], fmt: str = "human") -> str:
    if fmt == "json":
        return json.dumps(report, ensure_ascii=False, indent=2, default=str)
    analysis = report["analysis"]
    session = analysis["session_metrics"]
    lines = [
        "Telemetry Report",
        "================",
        f"gap seconds: {analysis['gap_seconds']}",
        f"invocations: {analysis['invocation_count']}",
        f"sessions: {session['session_count']}",
        f"calls/session avg: {_fmt(session['invocation_count_average'])}",
        f"calls/session p50/p90/p95: {session['invocation_count_p50']} / "
        f"{session['invocation_count_p90']} / {session['invocation_count_p95']}",
        "",
        "Command frequency:",
    ]
    for command, count in analysis["command_frequency"].items():
        lines.append(f"  {command}: {count}")
    lines.extend([
        "",
        "Follow-up:",
        f"  overall: {analysis['followup']['overall_count']}",
        f"  same target: {analysis['followup']['same_target_count']}",
        f"  different target: {analysis['followup']['different_target_count']}",
        "",
        "Expansion:",
        f"  depth escalation: {analysis['expansion']['depth_escalation_count']}",
        f"  path expansion: {analysis['expansion']['path_expansion_count']}",
        f"  empty result expansion: {analysis['expansion']['empty_result_expansion_count']}",
        "",
        "Path fan-out:",
        f"  groups: {analysis['path_fanout']['group_count']}",
    ])
    for group in analysis["path_fanout"]["groups"][:5]:
        lines.append(f"  {group['start_raw']}: {group['distinct_targets']} targets")
    lines.extend([
        "",
        "Batch exploration:",
        f"  multi-model sessions: {analysis['batch_exploration']['multi_model_session_count']}",
        f"  multi-field sessions: {analysis['batch_exploration']['multi_field_session_count']}",
        "",
        "Load overhead:",
        f"  load ms avg/p50/p90: {_fmt(analysis['load_overhead']['load_ms_average'])} / "
        f"{analysis['load_overhead']['load_ms_p50']} / {analysis['load_overhead']['load_ms_p90']}",
        f"  load/total ratio: {_fmt(analysis['load_overhead']['load_to_total_duration_ratio'])}",
        "",
        "Gap sensitivity:",
    ])
    for gap, metrics in report["sensitivity"].items():
        lines.append(
            f"  {gap}s: sessions={metrics['session_count']} "
            f"p50={metrics['invocation_count_p50']} p90={metrics['invocation_count_p90']}"
        )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
