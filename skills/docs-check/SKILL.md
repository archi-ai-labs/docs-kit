---
name: docs-check
description: Read-only validation of the docs/ structure. Runs the deterministic docs-kit validator script and explains each failure in plain language with a suggested fix — never edits anything. Use only when the user runs /docs-kit:docs-check or explicitly asks to validate/check docs consistency.
---

# docs-check — read-only structure validation

You are a **wrapper around the validator script, nothing more**. The script is
the source of truth for form — do not eyeball-validate in its place, do not add
findings it did not report, and **do not fix anything**. Fixing belongs to
`/docs-kit:docs-sync` or to the user.

## Step 1 — Run the validator

Resolve the plugin root (in order: `$CLAUDE_PLUGIN_ROOT` env var → two levels
above this SKILL.md → `find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit`
containing `.claude-plugin/plugin.json`), then:

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

Exit codes: `0` clean · `1` violations (one `FAIL [tag] file: message` line
each) · `2` setup error (usually: no `docs/` — suggest `/docs-kit:docs-init`).

## Step 2 — Report

**Clean run:** say so in one or two sentences, quoting the script's OK line
(file count). Relay any `NOTE [layout]` lines about missing standard folders as
informational. Remind the user the script checks form, not content quality.

**Violations:** for each FAIL line, produce:
1. The raw line (so the user can grep for it).
2. What it means in plain language — the tag explains the rule family:
   - `[ref]` — a `*_ref:` points to an id that doesn't exist (typo, deleted doc,
     or the referenced doc was never created), or an id is duplicated.
   - `[backlog]` — a Backlog item lost its traceability (`source_ref` must name
     the Decision for full lane, the Issue for fast lane).
   - `[frontmatter]` — required fields/enums/id-prefix broken for that doc type,
     or a Proposal lacks its "Alternatives considered" section.
   - `[audit-append]` — someone edited or deleted existing audit-log lines;
     the log is append-only history.
   - `[amended-by]` — an Architecture amendment entry doesn't cite an existing
     Decision — exactly the "only Decisions amend Architecture" rule.
3. A concrete suggested fix (which file, which field, what value).
4. Who should do it: mechanical fixes → offer to run `/docs-kit:docs-sync`;
   judgment calls (e.g. which Decision an amendment belongs to, whether audit
   history was rewritten intentionally) → the user.

End with the script's summary count. Change nothing on disk.
