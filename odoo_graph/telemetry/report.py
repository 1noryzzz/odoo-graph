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


def _json_obj(row: dict[str, Any], column: str) -> dict[str, Any]:
    raw = row.get(column)
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _argv(row: dict[str, Any]) -> list[str]:
    argv = _json_obj(row, "argv_json").get("argv") or []
    return [str(arg) for arg in argv]


def _arg_shape(row: dict[str, Any]) -> dict[str, Any]:
    return _json_obj(row, "argv_json").get("arg_shape") or {}


def _option_value(argv: list[str], *names: str) -> str | None:
    for idx, item in enumerate(argv):
        for name in names:
            if item == name and idx + 1 < len(argv):
                return argv[idx + 1]
            prefix = f"{name}="
            if item.startswith(prefix):
                return item[len(prefix):]
    return None


def _format_value(row: dict[str, Any]) -> str:
    value = _arg_shape(row).get("format")
    if value:
        return str(value)
    return _option_value(_argv(row), "--format", "-f") or "human"


def _db_value(row: dict[str, Any]) -> str:
    argv = _argv(row)
    if row["command"] == "dump":
        return _option_value(argv, "--database", "-d") or "<none>"
    return _option_value(argv, "--db") or "<none>"


def _out_dir_value(row: dict[str, Any]) -> str:
    return _option_value(_argv(row), "--out-dir", "-o") or "<auto>"


def _extra_value(row: dict[str, Any], key: str) -> Any:
    return _json_obj(row, "extra_json").get(key)


def _client_value(row: dict[str, Any]) -> str:
    explicit = _extra_value(row, "client")
    if explicit:
        return str(explicit)
    thread = row.get("codex_thread_id") or ""
    if thread.startswith("cursor:"):
        return "cursor"
    if thread.startswith("local:"):
        return "local"
    if thread:
        return "codex"
    return "unknown"


def _top_dimension(
    rows: list[dict[str, Any]],
    value_fn: Any,
    limit: int = 20,
) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    for row in rows:
        value = value_fn(row)
        counts[value] += 1
        if not row.get("success"):
            failures[value] += 1
    return [
        {"value": value, "count": count, "failures": failures[value]}
        for value, count in counts.most_common(limit)
    ]


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
    top_sessions: list[dict[str, Any]] = []
    command_sequences: list[dict[str, Any]] = []

    for session in sessions:
        rows_in_session = session["rows"]
        sequence = [r["command"] for r in rows_in_session]
        compact_sequence = [
            f"{r['command']}:{r.get('target_raw') or r.get('start_raw') or '-'}"
            for r in rows_in_session
        ]
        top_sessions.append({
            "session_key": session["session_key"],
            "thread_id": session["thread_id"],
            "client": _client_value(rows_in_session[0]),
            "started_at": session["started_at"],
            "ended_at": session["ended_at"],
            "invocation_count": len(rows_in_session),
            "commands": sequence,
            "sequence": compact_sequence,
        })
        command_sequences.append({
            "session_key": session["session_key"],
            "thread_id": session["thread_id"],
            "client": _client_value(rows_in_session[0]),
            "started_at": session["started_at"],
            "invocation_count": len(rows_in_session),
            "sequence": compact_sequence,
        })
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
    graph_source_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in flat:
        if row.get("duration_load_ms") is None:
            continue
        graph_source_groups[str(_extra_value(row, "graph_source") or "<unknown>")].append(row)
    graph_source_load_stats = []
    for graph_source, group_rows in graph_source_groups.items():
        group_loads = [r["duration_load_ms"] for r in group_rows]
        graph_source_load_stats.append({
            "graph_source": graph_source,
            "count": len(group_rows),
            "load_ms_average": _avg(group_loads),
            "load_ms_p50": statistics.median(group_loads) if group_loads else None,
            "load_ms_p90": _percentile(group_loads, 0.90),
            "load_ms_min": min(group_loads) if group_loads else None,
            "load_ms_max": max(group_loads) if group_loads else None,
        })

    failure_details = []
    for row in flat:
        if row.get("success"):
            continue
        failure_details.append({
            "id": row.get("id"),
            "started_at": row.get("started_at"),
            "command": row.get("command"),
            "target_raw": row.get("target_raw"),
            "result_status": row.get("result_status"),
            "error_category": row.get("error_category"),
            "exit_code": row.get("exit_code"),
            "client": _client_value(row),
            "cwd": _extra_value(row, "cwd"),
            "db": _db_value(row),
            "out_dir": _out_dir_value(row),
            "format": _format_value(row),
            "exception_type": _extra_value(row, "exception_type"),
            "traceback_tail": _extra_value(row, "traceback_tail"),
        })

    target_counts: Counter[tuple[str, str]] = Counter()
    target_failures: Counter[tuple[str, str]] = Counter()
    for row in flat:
        key = (row["command"], row.get("target_raw") or "<none>")
        target_counts[key] += 1
        if not row.get("success"):
            target_failures[key] += 1

    return {
        "gap_seconds": gap_seconds,
        "invocation_count": len(flat),
        "time_range": {
            "first_invocation": flat[0]["started_at"] if flat else None,
            "last_invocation": flat[-1]["started_at"] if flat else None,
        },
        "command_frequency": dict(Counter(row["command"] for row in flat).most_common()),
        "client_frequency": dict(Counter(_client_value(row) for row in flat).most_common()),
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
        "top_targets": [
            {
                "command": command,
                "target_raw": target,
                "count": count,
                "failures": target_failures[(command, target)],
            }
            for (command, target), count in target_counts.most_common(20)
        ],
        "top_sessions": sorted(
            top_sessions,
            key=lambda s: s["invocation_count"],
            reverse=True,
        )[:10],
        "failure_details": failure_details[:20],
        "graph_source_load_stats": sorted(
            graph_source_load_stats,
            key=lambda s: s["count"],
            reverse=True,
        )[:20],
        "format_usage": _top_dimension(flat, _format_value),
        "cwd_usage": _top_dimension(flat, lambda row: str(_extra_value(row, "cwd") or "<unknown>")),
        "db_usage": _top_dimension(flat, _db_value),
        "out_dir_usage": _top_dimension(flat, _out_dir_value),
        "command_sequences": sorted(
            command_sequences,
            key=lambda s: s["invocation_count"],
            reverse=True,
        )[:20],
        "top_transitions": [
            {"from": src, "to": dst, "count": count}
            for (src, dst), count in transitions.most_common(20)
        ],
    }


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
        f"first invocation: {analysis['time_range']['first_invocation']}",
        f"last invocation: {analysis['time_range']['last_invocation']}",
        f"sessions: {session['session_count']}",
        f"calls/session avg: {_fmt(session['invocation_count_average'])}",
        f"calls/session p50/p90/p95: {session['invocation_count_p50']} / "
        f"{session['invocation_count_p90']} / {session['invocation_count_p95']}",
        "",
        "Client frequency:",
    ]
    for client, count in analysis["client_frequency"].items():
        lines.append(f"  {client}: {count}")
    lines.extend([
        "",
        "Command frequency:",
    ])
    for command, count in analysis["command_frequency"].items():
        lines.append(f"  {command}: {count}")
    lines.extend([
        "",
        "Format usage:",
    ])
    for item in analysis["format_usage"][:8]:
        lines.append(
            f"  {item['value']}: {item['count']} "
            f"(failures={item['failures']})"
        )
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
        "Top targets:",
    ])
    for item in analysis["top_targets"][:10]:
        lines.append(
            f"  {item['command']} {item['target_raw']}: {item['count']} "
            f"(failures={item['failures']})"
        )
    lines.extend([
        "",
        "Top sessions:",
    ])
    for item in analysis["top_sessions"][:5]:
        lines.append(
            f"  {item['session_key']}: {item['invocation_count']} calls "
            f"[{item['client']}]"
        )
        lines.append(f"    {' -> '.join(item['commands'])}")
    lines.extend([
        "",
        "Failure details:",
    ])
    if analysis["failure_details"]:
        for item in analysis["failure_details"][:8]:
            detail = item.get("exception_type") or item.get("error_category")
            tail = item.get("traceback_tail") or ""
            lines.append(
                f"  #{item['id']} {item['command']} {item.get('target_raw')}: "
                f"{item['result_status']} ({detail})"
            )
            if tail:
                lines.append(f"    {tail}")
    else:
        lines.append("  none")
    lines.extend([
        "",
        "Graph source load stats:",
    ])
    for item in analysis["graph_source_load_stats"][:5]:
        lines.append(
            f"  {item['graph_source']}: n={item['count']} "
            f"avg={_fmt(item['load_ms_average'])}ms "
            f"p50={item['load_ms_p50']}ms p90={item['load_ms_p90']}ms"
        )
    lines.extend([
        "",
        "CWD usage:",
    ])
    for item in analysis["cwd_usage"][:5]:
        lines.append(
            f"  {item['value']}: {item['count']} "
            f"(failures={item['failures']})"
        )
    lines.extend([
        "",
        "DB usage:",
    ])
    for item in analysis["db_usage"][:5]:
        lines.append(
            f"  {item['value']}: {item['count']} "
            f"(failures={item['failures']})"
        )
    lines.extend([
        "",
        "Out-dir usage:",
    ])
    for item in analysis["out_dir_usage"][:5]:
        lines.append(
            f"  {item['value']}: {item['count']} "
            f"(failures={item['failures']})"
        )
    lines.extend([
        "",
        "Command sequences:",
    ])
    for item in analysis["command_sequences"][:5]:
        lines.append(
            f"  {item['session_key']}: "
            + " -> ".join(item["sequence"][:12])
        )
        if len(item["sequence"]) > 12:
            lines.append(f"    ... +{len(item['sequence']) - 12} more")
    lines.extend([
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
