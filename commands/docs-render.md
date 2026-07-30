---
description: Generate or refresh the HTML views of docs/ (index, current, changes) — deterministic, never edits markdown
---

Generate the docs-kit HTML views for this repository.

1. Resolve the renderer script, in order:
   - If the environment variable `CLAUDE_PLUGIN_ROOT` is set:
     `"$CLAUDE_PLUGIN_ROOT/scripts/docs_render.sh"`.
   - Otherwise: `find ~/.claude/plugins -type f -path '*docs-kit*/scripts/docs_render.sh' 2>/dev/null | head -1`.
2. Run it from the repository root: `bash "<script>" "$(pwd)"`.
3. On success, report the three generated files — `docs/index.html` (entry point),
   `docs/current.html`, `docs/changes.html` — and remind the user that the pages
   are a generated read model: the markdown stays the source of truth, and the
   HTML is refreshed by re-running this command (docs-sync also refreshes it).
4. On failure, relay the script's stderr and the fix: no `docs/` directory →
   run `/docs-kit:docs-init` first; no `python3` → install Python 3.

Never edit any markdown file as part of this command. User arguments, if any: $ARGUMENTS
