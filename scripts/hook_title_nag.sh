#!/usr/bin/env bash
# docs-kit Stop hook — a crew session ending with a title that no longer matches git.
#
# WHY WARN-ONLY (do not "fix" this into a block):
#   Same doctrine as every other hook here (EXECUTION §12). A Stop hook that
#   blocks teaches people to switch hooks off, which loses every warning at once.
#   Deterministic script only — this hook must NEVER call an LLM (no `claude -p`).
#
# stdin:  Claude Code hook JSON ({session_id, transcript_path, cwd, ...})
# stdout: hook JSON with a systemMessage carrying the /rename line, when the
#         session's own title disagrees with `scripts/crew name <role> --want`.
# Silent when the repo has no scripts/crew, or anything at all is uncertain.
# Always exits 0.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

command -v python3 >/dev/null 2>&1 || exit 0

exec python3 "$SCRIPT_DIR/hook_title_nag.py"
