---
name: docs-check
description: Read-only validation of the docs/ structure. Runs the deterministic validator and explains each failure in plain language with a suggested fix — never edits anything.
disable-model-invocation: true
---

# docs-check — read-only structure validation

You are a **wrapper around the validator script, nothing more**. The script is
the source of truth for form — do not eyeball-validate in its place, do not add
findings it did not report, and **do not fix anything**. Fixing belongs to
`/docs-kit:docs-sync` or to the user.

## Step 1 — Run the two deterministic checks

Resolve the plugin root (in order: `$CLAUDE_PLUGIN_ROOT` env var → two levels
above this SKILL.md → `find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit`
containing `.claude-plugin/plugin.json`), then:

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

Exit codes: `0` clean · `1` violations (one `FAIL [tag] file: message` line
each) · `2` setup error (usually: no `docs/` — suggest `/docs-kit:docs-init`).

Then check that the agent read model is current:

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" --check .
```

Exit codes: `0` current · `1` `docs/INDEX.md` missing or stale · `2` no `docs/`
· `3` no `python3` (say so and move on — it is not a docs problem).

**This is a second script, not a second opinion.** It writes nothing and it
rebuilds the index through the same code path the renderer uses, so it never
disagrees with what a real render would produce. The rule below still holds
exactly: report what the scripts said, add nothing, fix nothing.

## Step 2 — Report

**Clean run:** say so in one or two sentences, quoting the script's OK line
(file count). Relay `NOTE` lines as informational — they never affect the exit code:
- `NOTE [layout]` — a standard folder is missing.
- `NOTE [stale]` — a layer 1 doc carries `verified_at: <rev>` and some of the paths
  it names have changed since. Changed is not the same as wrong, which is why this
  warns instead of failing; the fix is to re-read those files and move `verified_at`
  forward, and `/docs-kit:docs-sync` is where that happens.

Remind the user the script checks form, not content quality.

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
   - `[amended-by]` — an `amended_by` or `rejected` entry doesn't cite an existing
     Decision — exactly the "only Decisions amend Architecture" rule.
   - `[anchor]` — a layer 1 doc names a path that no longer exists (a component's
     backticked `path/in/repo`, or a figure fence's `code:` header). The doc cannot
     be verified against anything until the path is corrected or the entry removed.
     Correcting a path is a layer 1 edit, so it goes through the Decision workflow
     like any other — the check tells you *that* it is wrong, never what it should say.
3. A concrete suggested fix (which file, which field, what value).
4. Who should do it: mechanical fixes → offer to run `/docs-kit:docs-sync`;
   judgment calls (e.g. which Decision an amendment belongs to, whether audit
   history was rewritten intentionally) → the user.

**Stale index (`--check` exit 1):** report it separately from the validator's
findings — it is not a violation of the docs, it means the generated read model
has fallen behind them. Say what it costs: `brief` and `docs-sync` read
`docs/INDEX.md` instead of globbing folders, so until it is regenerated they are
reading an answer that is out of date, and a wrong answer they trust is worse
than no answer. The fix is one command, and it belongs to
`/docs-kit:docs-render` or `/docs-kit:docs-sync` — not to this skill.

End with the script's summary count. Change nothing on disk.
