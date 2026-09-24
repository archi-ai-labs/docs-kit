---
name: docs-archive
description: Archive finished Layer 2 chains (Issue, Proposal, Decision, Backlog) after a chain-by-chain preview you approve; links follow each move.
disable-model-invocation: true
---

# docs-archive — move finished Layer 2 chains out of the hot set

This skill cleans up `20_issues/`, `21_proposals/`, `22_decisions/` and
`23_backlog/` by **chain** — Issue → Proposal → Decision → Backlog — rather than
file by file, and ends in a report whose shape is fixed in advance. It runs only
when the user types it.

Ground rules, all of them load-bearing:

- **The script decides; you relay, investigate and ask.** Every verdict comes from
  `docs_archive.py`, which prints the same plan `docs_close --archive` executes
  (STANDARD §2). Never `git mv` a Layer 2 document yourself — a hand move skips
  the link rewrite, and a missed rewrite is exactly how one real repo ended up
  with 44 broken links.
- **Nothing is written before the user approves the plan the preview printed.**
  The preview writes nothing; `--apply` writes exactly that plan.
- **Never edit layer 1 or `92_audit/`.** A link there that pointed at a moved
  document is listed in the report with its replacement path; the user decides.
- **Relay the report verbatim.** Its sections, tables and wording are the format
  the user reviews, run after run. Do not reorder, merge, translate or summarise
  it. What you add goes *after* it, in the two blocks defined below.

If there is no `docs/` here, stop and suggest `/docs-kit:docs-init`.

## Step 0 — Resolve the plugin root, look at the tree

Resolve the plugin root in order: `$CLAUDE_PLUGIN_ROOT` → two levels above this
SKILL.md → `find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit` containing
`.claude-plugin/plugin.json`.

```bash
git status --porcelain -- docs/
```

Uncommitted changes under `docs/` are not a blocker, but say so in one line: the
moves will land in the same diff, and a reviewer can no longer tell them apart.
Suggest committing first; proceed if the user does not want to.

## Step 1 — Preview

```bash
python3 "$PLUGIN_ROOT/scripts/docs_archive.py" .
```

Add `--all` only when the user asked for every chain in flight. Exit codes:
`0` nothing moves · `1` moves pending · `2` no `docs/` · `127` no `python3`
(say so and stop — nothing here can be done by hand safely).

Print the script's output as it is. Its sections come in this order. `Complete`,
`Needs a decision` and `In flight` always appear, and say so when they are empty;
the others appear only when they have something to say:

| Section | What it answers |
|---|---|
| header + folder table | how many documents leave each folder, before → after |
| `Recorded from commits` | `Closes:` trailers not yet recorded; they are written first, so their items can move in the same run |
| `Complete` | chains where every hot document moves — with the audit line or declaration that closed them |
| `Needs a decision` | chains that can never close by themselves, one row per reason, each with what would release it |
| `In flight` | chains held only by open work; nothing to do |
| `Links` | links the moves rewrite, and links in layer 1 / the audit log left for a person |

If the preview moves nothing and `Needs a decision` is empty, say so in one line
and stop. There is nothing to ask.

## Step 2 — Investigate what `Needs a decision` offers to settle

Read-only. Only rows whose *To release* column offers `--settle <ID>` — those are
the three shapes a person may declare finished, and the only ones this skill can
act on. For every other row (a missing audit line, a value outside its enum, a
stranded archived item) the report already names the fix, and it belongs to
`/docs-kit:docs-sync` or `/docs-kit:docs-check`, not here.

For each settle candidate, open the documents it names and decide which shape fits:

- **Approved Decision, no Backlog item cites it.** STANDARD §2 lists three shapes,
  none a broken chain: *retroactive record* (written during a docs migration after
  the fact — the body usually says so), *layer-1 only* (its
  `architecture_amendment` is applied — an `amended_by` entry in
  `02_architecture/` cites it), *recording shipped work* (the report's row already
  names the ticket that cites the Issue instead of the Decision). One shape with
  evidence → recommend settle. No shape fits → recommend keeping it hot, and say
  what is missing.
- **Rejected Decision.** Search its body for a reopen condition — "hoãn",
  "post-v1", "mở lại khi…", "revisit when…". Measured on a real repo, the one
  rejected Decision meant *deferred until a second process is needed*. A live
  condition → recommend keeping it hot, where someone will see it. None → settle.
- **Promoted Issue, nothing cites it.** Read the documents the report says
  mention it. If one absorbed the work (a ticket's body or audit line says it was
  merged in) → recommend settle, which sets `status: archived`. If nothing did, the
  Issue still needs a Backlog item; recommend keeping it, and say so.

Print this block after the report, one row per candidate:

```
### Settle candidates
| Id | Shape | Evidence | Recommendation |
|---|---|---|---|
| DECISION-006 | layer-1 only | amended_by của architecture.md cite nó (2026-08-30) | settle |
| DECISION-003 | rejected | "Điều kiện mở lại: cần process thứ hai" | keep hot |
```

Evidence is one concrete fact with its file — never "looks finished". It
becomes the reason column of the audit line if the chain is settled, so write it
in Vietnamese (STANDARD §11: audit entries explain) and as a reason a stranger
could check.

## Step 3 — Ask once

One AskUserQuestion call, up to two questions:

1. `header: "Archive"` — "Apply the preview: N documents move, M links rewritten?"
   Options: "Apply (Recommended)" and "Report only". Skip this question when the
   preview moves nothing.
2. `header: "Settle"`, `multiSelect: true` — "Which held chains are finished?"
   One option per candidate from Step 2, recommended ones first with
   `(Recommended)` in the label and the evidence in the description. At most 4 —
   the tool's ceiling; with more candidates, offer the four with the strongest
   evidence and list the rest in text for a later run. Skip when there are none.

This is a confirmation in the middle of a task, not argument collection, so use
AskUserQuestion even where the desktop app's skill-invocation note says
otherwise — the same reasoning `brief` gives for its gate. If the tool is
unavailable or returns nothing, ask the same questions in plain text, numbered,
and **end the turn**. A general "ok" approves the moves only, never a settle: a
settle is a declaration about one chain, and it needs that id chosen.

"Report only" on both → stop. The report above is the deliverable.

## Step 4 — Apply

```bash
python3 "$PLUGIN_ROOT/scripts/docs_archive.py" --apply \
  --settle DECISION-006 --why "layer-1 only: amended_by của architecture.md cite nó" .
```

One `--settle`/`--why` pair per chosen chain, in order; no pair when nothing was
chosen. The script re-plans from the tree as it stands, so if someone committed
since the preview, its numbers are the ones that are true — when they differ from
the preview, say which lines changed.

Exit `2` means a settle was refused and **nothing was written**; relay the
`Settle refused` table and stop. Do not retry without the refused id unless the
user says so — they approved one plan, and that would be a different one.

## Step 5 — Refresh and verify

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" "$(pwd)"
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
git status --porcelain -- docs/
```

The render is not optional: `INDEX.md` still lists the moved files at their old
paths, and `MAP.tsv` is what the Stop hook reads.

The validator's `NOTE [link]` lines matter here. Every link that resolved before
the run must resolve after it, except the layer 1 / audit-log rows the report
listed. A `[link]` note on any other file this run touched, or any new `FAIL`, is a
defect in the kit — say so plainly and offer `docs_feedback.sh new <slug>`
(STANDARD §12). Pre-existing findings are not this run's; mention their count only.

## Step 6 — Final report

Print the applied report from Step 4 verbatim, then exactly this block:

```
### Verify
- validator: <its summary line, verbatim>
- read models: INDEX.md, MAP.tsv regenerated        (or: stale — <why>)
- git: <n> renames, <m> modified — not committed
- layer 1 links left: <count from the Links section, or 0>
```

Then the commit, as a command the user runs — do not run it:

```bash
git add -A docs && git commit -m "docs: archive <n> finished layer-2 documents"
```

Stop there. Fixing the layer 1 links the report listed, writing a missing audit
line, or cutting a Backlog item for a held Issue are separate tasks; name them if
they exist, and do none of them unasked.
