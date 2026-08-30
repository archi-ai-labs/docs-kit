#!/usr/bin/env bash
# docs-kit — wrapper for the deterministic HTML renderer (docs_render.py).
#
# Usage: docs_render.sh [--check] [repo-root]     (default: current directory)
#
# Generates docs/index.html, docs/current.html, docs/changes.html, docs/INDEX.md
# and docs/MAP.tsv from the markdown in docs/. Read model only: never edits the
# source markdown. Same guarantees as the validator: no LLM, no network,
# deterministic output (only the generated-at stamp moves; override with
# DOCS_KIT_NOW for reproducibility).
#
# --check writes nothing and exits 1 if either text read model no longer matches
# the markdown. Put it in CI: skills read INDEX.md instead of globbing folders and
# the Stop hook reads MAP.tsv to find the document describing an edited file, so a
# stale INDEX.md feeds a wrong answer and a stale MAP.tsv suppresses a warning.
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
