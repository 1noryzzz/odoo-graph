"""Logging setup for odoo-graph.

Three things matter for a CLI tool:

1. **Default is informative, not spammy.** INFO level prints what command we
   ran, what data we read, and the headline counts. No DEBUG noise.
2. **One flag to dial verbosity.** ``-v`` (DEBUG), or ``--log-level``.
3. **Stderr only.** stdout is reserved for query payloads (so users can pipe
   ``odoo-graph field ... -f json | jq ...`` without grep-stripping logs).

The internal logger name is ``odoo_graph`` so all submodules pick it up via
``logging.getLogger(__name__)``.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional


_LOGGER_NAME = "odoo_graph"
_DATEFMT = "%H:%M:%S"
_FMT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"

# Map -v repetitions to log levels.
_VERBOSITY_LEVELS = {
    0: logging.INFO,
    1: logging.DEBUG,
    2: logging.DEBUG,  # reserved for future ultra-verbose levels
}


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger of the package logger.

    Submodules use ``log = get_logger(__name__)`` and inherit handlers.
    """
    if name is None:
        return logging.getLogger(_LOGGER_NAME)
    if name.startswith(_LOGGER_NAME):
        return logging.getLogger(name)
    return logging.getLogger(f"{_LOGGER_NAME}.{name}")


def setup_logging(level: str | int | None = None, verbosity: int = 0) -> logging.Logger:
    """Initialise the package logger. Idempotent (safe to call repeatedly).

    Priority: explicit ``level`` > verbosity flag (``-v``) > $ODOO_GRAPH_LOG >
    INFO default.

    Args:
        level: log level name ("DEBUG", "INFO", ...) or numeric.
        verbosity: 0/1/2 from CLI ``-v`` count.

    Returns:
        The package logger, ready to use.
    """
    if level is None:
        env = os.environ.get("ODOO_GRAPH_LOG")
        if env:
            level = env
        else:
            level = _VERBOSITY_LEVELS.get(min(verbosity, 2), logging.INFO)

    if isinstance(level, str):
        numeric = logging.getLevelName(level.upper())
        if not isinstance(numeric, int):
            numeric = logging.INFO
        level = numeric

    root = logging.getLogger(_LOGGER_NAME)
    root.setLevel(level)

    # Replace any pre-existing handlers we own to keep the call idempotent.
    for h in list(root.handlers):
        if getattr(h, "_odoo_graph_owned", False):
            root.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))
    handler._odoo_graph_owned = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    # Don't double-print via the root logger.
    root.propagate = False
    return root
