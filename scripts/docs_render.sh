#!/usr/bin/env bash
# docs-kit — wrapper for the deterministic HTML renderer (docs_render.py).
#
# Usage: docs_render.sh [repo-root]     (default: current directory)
#
# Generates docs/index.html, docs/current.html, docs/changes.html from the
# markdown in docs/. Read model only: never edits markdown. Same guarantees
# as the validator: no LLM, no network, deterministic output (only the
# generated-at stamp moves; override with DOCS_KIT_NOW for reproducibility).
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "docs-render: python3 not found — cannot render HTML views" >&2
  exit 3
fi

exec python3 "$SCRIPT_DIR/docs_render.py" "${1:-$(pwd)}"
