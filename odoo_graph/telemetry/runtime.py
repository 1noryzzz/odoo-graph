"""Runtime collection helpers for CLI invocations."""
from __future__ import annotations

import hashlib
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from odoo_graph import __version__
from odoo_graph.logging import get_logger

from .store import TELEMETRY_SCHEMA_VERSION, insert_invocation


TRACKED_COMMANDS = {"dump", "field", "model", "module", "context", "impact", "path", "overrides"}
DEFAULT_SESSION_GAP_SECONDS = 60

log = get_logger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _ms(seconds: float) -> int:
    return int(round(seconds * 1000))


def telemetry_enabled(args: Any) -> bool:
    if getattr(args, "no_telemetry", False):
        return False
    env = os.environ.get("ODOO_GRAPH_TELEMETRY")
    return env not in {"0", "false", "False", "no", "NO", "off", "OFF"}


def local_thread_scope() -> str:
    cwd = str(Path.cwd().resolve())
    digest = hashlib.sha1(cwd.encode("utf-8")).hexdigest()[:12]
    return f"local:{digest}"


def client_context() -> dict[str, str | None]:
    cursor_conversation_id = os.environ.get("CURSOR_CONVERSATION_ID")
    if cursor_conversation_id:
        return {
            "client": "cursor",
            "thread_scope": f"cursor:{cursor_conversation_id}",
            "cursor_conversation_id": cursor_conversation_id,
            "cursor_agent": os.environ.get("CURSOR_AGENT"),
        }
    codex_thread_id = os.environ.get("CODEX_THREAD_ID")
    if codex_thread_id:
        return {
            "client": "codex",
            "thread_scope": codex_thread_id,
            "cursor_conversation_id": None,
            "cursor_agent": None,
        }
    return {
        "client": "local",
        "thread_scope": local_thread_scope(),
        "cursor_conversation_id": None,
        "cursor_agent": None,
    }


def _arg_shape(args: Any) -> dict[str, Any]:
    return {
        "has_max_depth": hasattr(args, "max_depth"),
        "has_max_paths": hasattr(args, "max_paths"),
        "has_allow_kinds": bool(getattr(args, "allow_kinds", None)),
        "format": getattr(args, "format", None),
    }


def _argv(argv: list[str] | None) -> list[str]:
    return list(sys.argv[1:] if argv is None else argv)


@dataclass
class InvocationRecorder:
    command: str
    argv: list[str]
    started_at: str = field(default_factory=_utc_now_iso)
    start_monotonic: float = field(default_factory=time.monotonic)
    db_path: str | None = None
    duration_load_ms: int | None = None
    duration_query_ms: int | None = None
    duration_output_ms: int | None = None
    target_raw: str | None = None
    target_kind: str | None = None
    target_model: str | None = None
    target_field: str | None = None
    target_method: str | None = None
    target_module: str | None = None
    start_raw: str | None = None
    start_kind: str | None = None
    start_model: str | None = None
    start_field: str | None = None
    max_depth: int | None = None
    max_paths: int | None = None
    allow_kinds: str | None = None
    empty_result: bool = False
    result_size: int | None = None
    result_status: str | None = None
    error_category: str | None = None
    argv_json: dict[str, Any] = field(default_factory=dict)
    target_meta_json: dict[str, Any] | None = None
    result_summary_json: dict[str, Any] | None = None
    extra_json: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_args(cls, args: Any, argv: list[str] | None) -> "InvocationRecorder":
        rec = cls(
            command=args.cmd,
            argv=_argv(argv),
            target_raw=getattr(args, "target", None),
            start_raw=getattr(args, "start", None),
            max_depth=getattr(args, "max_depth", None),
            max_paths=getattr(args, "max_paths", None),
            allow_kinds=getattr(args, "allow_kinds", None),
        )
        rec.argv_json = {
            "argv": rec.argv,
            "arg_shape": _arg_shape(args),
        }
        rec.extra_json = {"cwd": str(Path.cwd().resolve())}
        return rec

    def add_extra(self, **values: Any) -> None:
        self.extra_json.update({k: v for k, v in values.items() if v is not None})

    def record_load(self, seconds: float, graph: Any, source: str) -> None:
        self.duration_load_ms = _ms(seconds)
        self.add_extra(
            graph_nodes=graph.g.number_of_nodes(),
            graph_edges=graph.g.number_of_edges(),
            graph_cache_key=str(Path(source).expanduser().resolve()),
            graph_source=str(Path(source).expanduser().resolve()),
            graph_cache_hit=False,
        )

    def add_query_seconds(self, seconds: float) -> None:
        value = _ms(seconds)
        self.duration_query_ms = value if self.duration_query_ms is None else self.duration_query_ms + value

    def add_output_seconds(self, seconds: float) -> None:
        value = _ms(seconds)
        self.duration_output_ms = value if self.duration_output_ms is None else self.duration_output_ms + value

    def set_target(
        self,
        *,
        kind: str | None = None,
        raw: str | None = None,
        model: str | None = None,
        field: str | None = None,
        method: str | None = None,
        module: str | None = None,
    ) -> None:
        if raw is not None:
            self.target_raw = raw
        self.target_kind = kind
        self.target_model = model
        self.target_field = field
        self.target_method = method
        self.target_module = module

    def set_start(
        self,
        *,
        kind: str | None = None,
        raw: str | None = None,
        model: str | None = None,
        field: str | None = None,
    ) -> None:
        if raw is not None:
            self.start_raw = raw
        self.start_kind = kind
        self.start_model = model
        self.start_field = field

    def set_result(
        self,
        *,
        summary: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
        size: int | None = None,
        empty: bool = False,
    ) -> None:
        self.result_summary_json = summary
        self.target_meta_json = meta
        self.result_size = size
        self.empty_result = empty

    def set_error(self, result_status: str, error_category: str) -> None:
        self.result_status = result_status
        self.error_category = error_category

    def finish(self, exit_code: int, exc: BaseException | None = None) -> None:
        ended_at = _utc_now_iso()
        success = exit_code == 0
        if exc is not None:
            self.result_status = "unexpected_error"
            self.error_category = "unexpected"
            self.add_extra(
                exception_type=type(exc).__name__,
                traceback_tail="".join(
                    traceback.format_exception_only(type(exc), exc)
                ).strip(),
            )
        elif self.result_status is None:
            if success:
                self.result_status = "success_empty" if self.empty_result else "success_non_empty"
            elif exit_code == 2:
                self.result_status = "usage_error"
                self.error_category = "usage_error"
            else:
                self.result_status = "query_error"
                self.error_category = "invalid_query"
        if self.error_category is None:
            self.error_category = "none" if success else "unexpected"

        context = client_context()
        codex_thread_id = os.environ.get("CODEX_THREAD_ID")
        codex_turn_id = os.environ.get("CODEX_TURN_ID")
        thread_scope = context["thread_scope"]
        session_key = (
            f"{codex_thread_id}:{codex_turn_id}"
            if codex_thread_id and codex_turn_id
            else thread_scope if context["client"] == "cursor" else None
        )
        self.add_extra(
            client=context["client"],
            cursor_conversation_id=context["cursor_conversation_id"],
            cursor_agent=context["cursor_agent"],
        )
        row = {
            "telemetry_schema_version": TELEMETRY_SCHEMA_VERSION,
            "package_version": __version__,
            "entrypoint": "cli",
            "started_at": self.started_at,
            "ended_at": ended_at,
            "duration_total_ms": _ms(time.monotonic() - self.start_monotonic),
            "duration_load_ms": self.duration_load_ms,
            "duration_query_ms": self.duration_query_ms,
            "duration_output_ms": self.duration_output_ms,
            "codex_thread_id": thread_scope,
            "codex_turn_id": codex_turn_id,
            "session_key": session_key,
            "session_gap_seconds": DEFAULT_SESSION_GAP_SECONDS,
            "command": self.command,
            "target_raw": self.target_raw,
            "target_kind": self.target_kind,
            "target_model": self.target_model,
            "target_field": self.target_field,
            "target_method": self.target_method,
            "target_module": self.target_module,
            "start_raw": self.start_raw,
            "start_kind": self.start_kind,
            "start_model": self.start_model,
            "start_field": self.start_field,
            "max_depth": self.max_depth,
            "max_paths": self.max_paths,
            "allow_kinds": self.allow_kinds,
            "success": 1 if success else 0,
            "exit_code": exit_code,
            "result_status": self.result_status,
            "error_category": self.error_category,
            "empty_result": 1 if self.empty_result else 0,
            "result_size": self.result_size,
            "argv_json": self.argv_json,
            "target_meta_json": self.target_meta_json,
            "result_summary_json": self.result_summary_json,
            "extra_json": self.extra_json,
        }
        try:
            insert_invocation(row, self.db_path)
        except Exception as write_exc:  # pragma: no cover - defensive path
            log.warning("telemetry write failed: %s", write_exc)


def field_meta(field_node: dict[str, Any], *, upstream_count: int | None = None) -> dict[str, Any]:
    return {
        "type": field_node.get("type"),
        "is_compute": bool(field_node.get("compute")),
        "is_related": bool(field_node.get("related")),
        "is_inherited": bool(field_node.get("inherited")),
        "is_delegated": bool(field_node.get("inherited_from_model")),
        "has_depends": bool(upstream_count),
        "module": field_node.get("module"),
    }


def model_meta(model_node: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_abstract": bool(model_node.get("abstract")),
        "is_transient": bool(model_node.get("transient")),
        "has_inherit": bool(model_node.get("inherit")),
        "has_inherits": bool(model_node.get("inherits")),
        "original_module": model_node.get("original_module"),
    }


def dump_result_size(summary: dict[str, Any] | None) -> int:
    if not summary:
        return 0
    return int(summary.get("models") or 0) + int(summary.get("fields") or 0)


def count_values(values: Iterable[Any]) -> int:
    return sum(1 for _ in values)
