#!/usr/bin/env bash
# docs-kit — wrapper for the deterministic HTML renderer (docs_render.py).
#
# Usage: docs_render.sh [--check] [repo-root]     (default: current directory)
#
# Generates docs/index.html, docs/current.html, docs/changes.html and
# docs/INDEX.md from the markdown in docs/. Read model only: never edits the
# source markdown. Same guarantees as the validator: no LLM, no network,
# deterministic output (only the generated-at stamp moves; override with
# DOCS_KIT_NOW for reproducibility).
#
# --check writes nothing and exits 1 if docs/INDEX.md no longer matches the
# markdown. Put it in CI: skills read that index instead of globbing folders,
# so a stale one silently feeds them a wrong answer.
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "docs-render: python3 not found — cannot render HTML views" >&2
  exit 3
fi

# Pass every argument through — "${1:-...}" would silently swallow the repo root
# whenever a flag came first, so `--check <root>` checked the wrong tree.
# docs_render.py already falls back to the current directory when given no root.
exec python3 "$SCRIPT_DIR/docs_render.py" "$@"
