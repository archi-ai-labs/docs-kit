#!/usr/bin/env bash
# docs-kit Stop hook — end-of-turn scan for undocumented sensitive changes.
#
# WHY WARN-ONLY (do not "fix" this into a block):
#   These enforcement rules have not been battle-tested across real projects yet.
#   Blocking on a false positive teaches users to disable the hook entirely, which
#   loses ALL enforcement. So we warn now, and only promote to block after the
#   trigger rules have been tuned in practice. Deterministic script only — this
#   hook must NEVER call an LLM (no `claude -p`).
#
# stdin:  Claude Code hook JSON ({session_id, transcript_path, cwd, ...})
# stdout: hook JSON with a systemMessage reminding the user to run
#         /docs-kit:docs-sync — only when the session edited files in sensitive
#         zones (default **/schema/**, **/api/**, **/migrations/**; configurable
#         via .docs-kit.json) WITHOUT creating or referencing any Issue/Decision.
# Silent when the repo has no docs-kit skeleton. Always exits 0.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# No python3 → skip silently rather than risk breaking the session.
command -v python3 >/dev/null 2>&1 || exit 0

# exec preserves stdin (the hook JSON) for the python worker.
exec python3 "$SCRIPT_DIR/hook_stop_scan.py"
