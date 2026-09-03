#!/usr/bin/env bash
# docs-kit Stop hook — end-of-turn scan for edits to code documents claim to describe.
#
# WHY WARN-ONLY (do not "fix" this into a block):
#   These enforcement rules have not been battle-tested across real projects yet.
#   Blocking on a false positive teaches users to disable the hook entirely, which
#   loses ALL enforcement. So we warn now, and only promote to block after the
#   trigger rules have been tuned in practice. Deterministic script only — this
#   hook must NEVER call an LLM (no `claude -p`).
#
# stdin:  Claude Code hook JSON ({session_id, transcript_path, cwd, ...})
# stdout: hook JSON with a systemMessage pointing at /docs-kit:docs-sync when the
#         session edited a file some document claims in docs/MAP.tsv (§10) and did
#         not also edit that document; or, when MAP.tsv is missing in a session
#         that touched code, one line pointing at /docs-kit:docs-render.
# Silent when the repo has no docs-kit skeleton. Always exits 0.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# No python3 → skip silently rather than risk breaking the session.
command -v python3 >/dev/null 2>&1 || exit 0

# exec preserves stdin (the hook JSON) for the python worker.
exec python3 "$SCRIPT_DIR/hook_stop_scan.py"
