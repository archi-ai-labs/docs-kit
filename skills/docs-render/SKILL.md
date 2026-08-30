---
name: docs-render
description: Generate or refresh the read models of docs/ — index.html, current.html, changes.html, INDEX.md and MAP.tsv — deterministic, never edits the source markdown
disable-model-invocation: true
---

Generate the docs-kit read models for this repository.

1. Resolve the renderer script, in order:
   - If the environment variable `CLAUDE_PLUGIN_ROOT` is set:
     `"$CLAUDE_PLUGIN_ROOT/scripts/docs_render.sh"`.
   - Otherwise: `find ~/.claude/plugins -type f -path '*docs-kit*/scripts/docs_render.sh' 2>/dev/null | head -1`.
2. Run it from the repository root: `bash "<script>" "$(pwd)"`.
3. On success, report the five generated files — `docs/index.html` (entry point),
   `docs/current.html`, `docs/changes.html`, `docs/INDEX.md`, and `docs/MAP.tsv` —
   and remind the user that all five are a generated read model: the markdown stays
   the source of truth, and they are refreshed by re-running this command (docs-sync
   also refreshes them).

   The three pages are the read model for people. The two text files are the ones
   for agents and hooks (STANDARD §10):
   - **`docs/INDEX.md`** — one line per document, so a skill can find the ids it
     needs without globbing a folder. A stale one is worse than a missing one,
     because the next agent trusts it.
   - **`docs/MAP.tsv`** — one line per path a layer 1 document claims, which is how
     the Stop hook knows whether an edited file is described anywhere. A stale one
     makes the hook *quieter*, so it fails in the direction nobody notices.
4. On failure, relay the script's stderr and the fix: no `docs/` directory →
   run `/docs-kit:docs-init` first; no `python3` → install Python 3.

Never edit any markdown file as part of this command. User arguments, if any: $ARGUMENTS
