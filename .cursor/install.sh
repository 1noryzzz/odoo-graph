#!/usr/bin/env bash
# Idempotent Cloud Agent / environment-build bootstrap for odoo-graph.
# Recurring builds start from a base image that does not ship `uv`, and
# agent shells typically omit ~/.local/bin from PATH.
set -euo pipefail

export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="${HOME}/.local/bin" sh
fi

uv_bin="$(command -v uv)"
if [[ "${uv_bin}" == "${HOME}/.local/bin/uv" && ! -x /usr/local/bin/uv ]]; then
  if [[ -w /usr/local/bin ]]; then
    install -m 755 "${HOME}/.local/bin/uv" /usr/local/bin/uv
    if [[ -x "${HOME}/.local/bin/uvx" ]]; then
      install -m 755 "${HOME}/.local/bin/uvx" /usr/local/bin/uvx
    fi
  else
    sudo install -m 755 "${HOME}/.local/bin/uv" /usr/local/bin/uv
    if [[ -x "${HOME}/.local/bin/uvx" ]]; then
      sudo install -m 755 "${HOME}/.local/bin/uvx" /usr/local/bin/uvx
    fi
  fi
fi

uv sync --extra dev
