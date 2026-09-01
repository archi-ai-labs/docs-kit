#!/usr/bin/env bash
# docs-kit PreToolUse hook (Bash) — the crew resource-guard.
#
# WHY WARN-ONLY (always, in 0.26.0 — no enforce path for this hook):
#   It matches substring patterns over one Bash command, so it measures the
#   cooperative and misses the forgetful — a wrapper script slips through
#   unlogged (EXECUTION §8's honest ceiling). A deny built on that evidence
#   would punish exactly the sessions that cooperate. Deterministic script
#   only — never calls an LLM.
#
# stdin:  Claude Code hook JSON ({tool_name, tool_input, cwd, ...})
# stdout: hook JSON with a warning systemMessage when a command matches a
#         declared resource's patterns and nobody holds that resource's lock.
# Silent unless the repo's .docs-kit.json has a `crew` key. Always exits 0.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# No python3 → skip silently rather than risk breaking the session.
command -v python3 >/dev/null 2>&1 || exit 0

# exec preserves stdin (the hook JSON) for the python worker.
exec python3 "$SCRIPT_DIR/hook_resource_guard.py"
