#!/usr/bin/env bash
# docs-kit — wrapper for the deterministic half of docs-sync (docs_close.py).
#
# Usage: docs_close.sh [--apply] [--archive] [repo-root]   (default: report, .)
#
# Reads `Closes: BACKLOG-NNN` trailers out of git history and records those
# completions — `status: done` plus one appended audit line citing the commit sha.
# With --archive it also moves terminal documents into `_archive/`.
#
# Everything it does is decided by facts already in the repo: a trailer the author
# wrote, a status field, an audit line that exists or does not. It never writes to
# layer 1, never creates an Issue, and never invents an audit line for work no
# commit claims — those are judgements and they stay in /docs-kit:docs-sync.
#
# Idempotent by construction: a completion already recorded is skipped, so the
# whole history can be re-scanned every run without needing state.
#
# Exit: 0 = nothing to do, or applied · 1 = pending changes (report mode; usable
#       as a CI gate) · 2 = setup error · 3 = python3 missing
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "docs-close: python3 not found — cannot read commit trailers" >&2
  exit 3
fi

exec python3 "$SCRIPT_DIR/docs_close.py" "$@"
