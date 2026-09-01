#!/usr/bin/env bash
# docs-kit PreToolUse hook (AskUserQuestion) — the crew explain-gate.
#
# WHY WARN-ONLY BY DEFAULT (do not "fix" this into a global block):
#   STANDARD §8 doctrine — blocking on a false positive teaches users to
#   disable the hook entirely, which loses ALL enforcement. Promotion to a
#   real deny is per repo, by flag: `.docs-kit.json` → "crew": {"enforce": true}
#   (EXECUTION §8). Deterministic script only — never calls an LLM.
#
# stdin:  Claude Code hook JSON ({tool_name, tool_input, transcript_path, cwd, ...})
# stdout: hook JSON — a warning systemMessage, or (enforce only) a deny.
# Silent unless the repo's .docs-kit.json has a `crew` key. Always exits 0.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# No python3 → skip silently rather than risk breaking the session.
command -v python3 >/dev/null 2>&1 || exit 0

# exec preserves stdin (the hook JSON) for the python worker.
exec python3 "$SCRIPT_DIR/hook_explain_gate.py"
