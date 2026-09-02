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

## Step 1 — Run the three deterministic checks

Resolve the plugin root (in order: `$CLAUDE_PLUGIN_ROOT` env var → two levels
above this SKILL.md → `find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit`
containing `.claude-plugin/plugin.json`), then:

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

Run it **without `--strict`**. That flag exists for CI, where a broken link should
stop a merge; here the user is asking what state their docs are in, and the default
mode answers that without pretending every finding is equally urgent.

Exit codes: `0` clean · `1` violations (one `FAIL [tag] file: message` line
each) · `2` setup error (usually: no `docs/` — suggest `/docs-kit:docs-init`).

The script reports at two severities, and the line between them is **names vs links**
(STANDARD §7). `FAIL` means a name is wrong, which silently merges two different
things and cannot be recovered from downstream. `NOTE` means a link is wrong, which
is one broken edge, visible the moment anyone follows it, and harmless until then.
Both are worth relaying. Only `FAIL` is worth stopping for.

Then check that the agent read model is current:

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" --check .
```

Exit codes: `0` current · `1` `docs/INDEX.md` or `docs/MAP.tsv` missing or stale ·
`2` no `docs/` · `3` no `python3` (say so and move on — it is not a docs problem).

Then, when any `04_api/` doc declares `generated_from:`, check the contracts against
the artifacts they defer their volatile half to:

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" --check-api .
```

Exit `0` match (or nothing declares an artifact) · `1` drift, or an artifact that
could not be read. Two kinds of drift, and they mean different things — say which:
an operation that is **live but undocumented** is the §6 trigger firing after the
fact, and an operation **documented but absent** means the contract states something
untrue.

**These are more scripts, not more opinions.** Both `--check` modes write nothing
and go through the same code paths a real render uses, so neither can disagree with
one. The rule at the top still holds exactly: report what the scripts said, add
nothing, fix nothing.

## Step 2 — Report

**Clean run:** say so in one or two sentences, quoting the script's OK line
(file count). A run with `NOTE` lines and no `FAIL` is still a clean run — say that
plainly rather than presenting the notes as failures the user got away with.

Relay every `NOTE` line. They never affect the exit code, and they come in two
families. The **soft findings** — `NOTE [ref]`, `NOTE [backlog]`, `NOTE [anchor]`,
`NOTE [amended-by]`, and `NOTE [frontmatter]` for any field other than `id` — are the
same checks §7 lists as soft: a link that resolves to nothing, a required field left
out, a path that has moved. Explain each one the way the FAIL list below does, and say
what it costs: a reader who follows that edge lands nowhere. Then leave the decision
with the user. These are worth fixing when someone is already in the file, not worth
a round trip of their own.

The rest are **informational about the repo**, not about a document:
- `NOTE [layout]` — a folder this repo's profile calls for is missing. Which folders
  those are comes from `owns` in `.docs-kit.json` (STANDARD §9.1); a repo that
  declares nothing is held to all 17. A folder *outside* the profile is never
  reported, so this line always means something is genuinely absent.
- `NOTE [profile]` — the repo shows a surface `owns` does not account for. Only the
  growth direction is checked, so this means "declare more", never "declare less".
- `NOTE [stale]` — a layer 1 doc carries `verified_at: <rev>` and some of the paths
  it names have changed since. Changed is not the same as wrong, which is why this
  warns instead of failing; the fix is to re-read those files and move `verified_at`
  forward, and `/docs-kit:docs-sync` is where that happens.

Remind the user the script checks form, not content quality.

**Violations:** for each FAIL line, produce:
1. The raw line (so the user can grep for it).
2. What it means in plain language — the tag explains the rule family:
   - `[ref]` — an id is duplicated, so every reference to it is now ambiguous and
     neither reference looks wrong; or one component name is declared in two
     architecture docs with **conflicting** backticked paths. A name repeated with no
     path of its own is a re-mention, which a cross-cutting flows document has to do,
     and the script does not report it.
   - `[frontmatter]` — a doc has no `id:`, so nothing can refer to it; or its `id:`
     prefix does not match its folder; or a `lane`/`status`/`outcome` value is outside
     its enum.
   - `[audit-append]` — someone edited or deleted existing audit-log lines;
     the log is append-only history.
   - `[profile]` — a token in `owns` the standard does not define. A typo there
     silently drops a whole folder from the scaffold.
3. A concrete suggested fix (which file, which field, what value).
4. Who should do it: mechanical fixes → offer to run `/docs-kit:docs-sync`;
   judgment calls (e.g. whether two docs describing one component name should merge,
   whether audit history was rewritten intentionally) → the user.

Correcting a documented path is a layer 1 edit, so it goes through the Decision
workflow like any other — every check here tells you *that* something is wrong,
never what it should say.

**Stale read model (`--check` exit 1):** report it separately from the validator's
findings — it is not a violation of the docs, it means a generated read model has
fallen behind them. The script names which one, and they cost different things:

- **`docs/INDEX.md`** — `brief` and `docs-sync` read it instead of globbing folders,
  so until it is regenerated they are reading an answer that is out of date, and a
  wrong answer they trust is worse than no answer.
- **`docs/MAP.tsv`** — the Stop hook reads it to decide whether an edited file is
  described by any document. A stale map does not produce wrong warnings; it
  produces **missing** ones, which is the failure nobody notices. Say this
  explicitly: a quiet hook looks exactly like a clean session.

The fix is one command either way, and it belongs to `/docs-kit:docs-render` or
`/docs-kit:docs-sync` — not to this skill.

**When the finding is against the kit, not the repo.** Exit 2 from a script that
should have run, or a `FAIL` the user demonstrates is wrong about a document the
standard permits, is a problem with docs-kit — STANDARD §12. Say so, and offer
`docs_feedback.sh new <slug>`; the user decides whether to file. Do not soften a
finding into "probably a kit bug" to avoid reporting it: the script's output is
relayed verbatim either way, and only the interpretation changes.

End with the script's summary count. Change nothing on disk.
