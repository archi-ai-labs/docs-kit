#!/usr/bin/env bash
# docs-kit PostToolUse hook (Edit|Write) — warn when docs/02_architecture/ is edited.
#
# WHY WARN-ONLY (do not "fix" this into a block):
#   These enforcement rules have not been battle-tested across real projects yet.
#   Blocking on a false positive teaches users to disable the hook entirely, which
#   loses ALL enforcement. So we warn now, and only promote to block after the
#   trigger rules have been tuned in practice. Deterministic script only — this
#   hook must NEVER call an LLM (no `claude -p`).
#
# stdin:  Claude Code hook JSON ({tool_name, tool_input:{file_path}, ...})
# stdout: hook JSON with systemMessage (user-facing) + additionalContext (agent-facing)
#         when the edited path is under docs/02_architecture/; nothing otherwise.
# Always exits 0 — a hook failure must never break the user's session.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# No python3 → skip silently rather than risk breaking the session.
command -v python3 >/dev/null 2>&1 || exit 0

# exec preserves stdin (the hook JSON) for the python worker.
exec python3 "$SCRIPT_DIR/hook_architecture_warn.py"
