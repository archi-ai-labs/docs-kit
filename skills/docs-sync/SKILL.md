---
name: docs-sync
description: Reconcile docs/ with what this session actually did — update Backlog statuses, append audit entries, create retroactive Issues, apply pending Architecture amendments.
disable-model-invocation: true
---

# docs-sync — reconcile docs/ with this session's work

This is the **writing** skill of docs-kit. It runs inside the session that did
the work, because that session has the context. Ground rules come from the
model (STANDARD.md at the plugin root; digest in `docs/README.md`):

- `docs/92_audit/` is **append-only**: add lines at the end of the log file,
  never edit, reorder, or delete existing lines.
- `docs/02_architecture/` and `docs/03_business-logic/` may be touched **only** via the approved-Decision path
  in Step 4 — nothing else in this skill edits layer 1.
- Never fabricate history: no retroactive Decisions, no invented approvals.
  When traceability is missing, create an **Issue** and tell the user.
- New IDs: next number per type = highest existing + 1, zero-padded to 3 digits
  (scan `grep -rh '^id:' docs/` to find the maximum). Never renumber existing ids.

If there is no `docs/` skeleton here, stop and suggest `/docs-kit:docs-init`.

## Step 1 — Inventory what the session did

From the conversation context, list concretely: features/fixes completed, files
changed, decisions the user approved in chat. Corroborate with evidence where
available: `git status --porcelain` and `git diff --stat HEAD` (or recent
commits made this session). This inventory drives every step below — when the
session did nothing code-related, say so and stop after Step 4.

## Step 2 — Backlog statuses

**Read `docs/INDEX.md`, not the folder.** It carries one line per Backlog item —
id, status, source_ref, file, description — which is everything needed to decide
*which* items this session touched. Open only those files. Globbing
`docs/23_backlog/*.md` costs a whole file per item and only gets worse; the index
costs a line (STANDARD §10).

If `docs/INDEX.md` does not exist, the repo has not been rendered since the index
was introduced — say so, and fall back to the folder for this one run.

For each item whose work happened this session:
- work finished → `status: done`
- work started but unfinished → `status: in-progress`

For every item flipped to `done`, append one line to `docs/92_audit/LOG.md`
(format: `YYYY-MM-DD | what happened | ref | deviation ("-" if none) | why`).
The ref column carries the Backlog id and its source Decision/Issue. If what
was shipped deviates from what the Decision/Backlog described, state the
deviation and why — honestly.

## Step 3 — Work that had no Backlog item

For each piece of completed work with no matching Backlog item, create an Issue.

The mechanics — id allocation, file naming, frontmatter, the lane test, and the
routing that follows it — are in `references/issue-capture.md` at the plugin
root (resolve the root as in docs-init Step 0). `brief` reads the same file from
the forward direction; keeping one copy is what stops the two paths from
drifting.

What is specific to this skill:

- The body must note **"Created retroactively by docs-sync — the work was done
  before this Issue existed."** The forward path has no such line, and the
  distinction matters when someone later audits the chain.
- The work is already finished, so a fast-lane Backlog item is written at
  `status: done` **with** its audit line — not `open` without one.
- Full lane → **stop at the Issue** (`status: open`) and flag it prominently in
  the report: full-lane work happened without a Proposal/Decision. Do not
  fabricate the missing Proposal/Decision — that is the user's call.

## Step 4 — Pending Architecture amendments

For each `docs/22_decisions/*.md` with `outcome: approved` and an
`architecture_amendment` that is neither empty nor `none`: check whether the
relevant `docs/02_architecture/` doc's `amended_by` already cites its id. If
not — and the Decision was approved in or before this session — apply the
amendment now:
1. Update the relevant Architecture doc body per the Decision.
2. Append to its `amended_by`: `- YYYY-MM-DD DECISION-NNN <one-line summary>`.

This is the only legitimate write path into layer 1. The PostToolUse hook will
still print its warning — expected; mention the Decision ref in your report.

## Step 5 — Architecture drift: does the doc still match the code?

Only when this session changed code. The Architecture doc describes the source;
the source moves and the doc does not, so this step compares them and **reports**
— it never edits `docs/02_architecture/` outside the Decision path in Step 4.

**Let the validator scope this step first.** Run it (resolve the plugin root as in
docs-init Step 0):

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

Two kinds of line tell you where to look, deterministically and for free:

- `FAIL [anchor] <file>: names '<path>', which does not exist` — a documented path
  moved or was deleted. This is certain, not a guess.
- `NOTE [stale] <file>: verified_at <rev> — N of the paths this doc names changed`
  — the code under this document has moved since anyone last read it.

**Read code to check a document only where those lines point.** Re-reading every
Architecture doc every session is the most expensive thing this skill can do, and
it is what these anchors exist to make unnecessary. When the validator is silent
and this session touched nothing under a documented path, say so and move on.

Then, for the documents in scope, read `components` and `data_flow` from
`docs/02_architecture/*.md` and the ```` ```flow ```` blocks in
`docs/01_products/*.md`, and check them against what this session actually touched:

- a component whose backticked path **no longer exists**, or moved;
- a new component-sized thing added this session (a new service, datastore,
  queue, or scheduled worker) that is absent from `components`. When
  `02_architecture/` holds one document per service, it belongs to the document
  for the service that contains it — and a whole new service is a new document,
  not a row appended to someone else's (STANDARD §4);
- a new call between two services documented in *different* architecture docs:
  the edge belongs to the **caller's** document, the contract to the callee's.
  Writing it in both is the duplication the split exists to prevent;
- a `data_flow` edge whose call site was deleted, or a new call/publish between
  two documented components with no edge for it;
- a business-flow step that no longer matches the code path it names;
- a component whose description is now false — the behaviour changed underneath
  a sentence that still claims the old one.

For each finding, judge the lane by the usual two-question test. Documentation
that has fallen out of date is itself an Issue: create
`docs/20_issues/ISSUE-NNN-<slug>.md` describing the drift concretely (what the
doc says, what the code now does, the file to read), and let the Decision
workflow decide the amendment. Do not quietly rewrite layer 1 to match the code
— that is exactly the edit the model exists to prevent.

Report every finding even when you create no Issue for it.

**When you did re-read the code behind a document and it still describes it
correctly, move `verified_at` forward** to the current rev:

```bash
git rev-parse --short HEAD
```

That is a metadata field, not a change to layer 1's content — it records *when the
document was last checked*, which is the only thing that stops the same document
being re-read every session forever. Do not touch it for a document you did not
actually read.

## Step 6 — Archive what can no longer change

Terminal documents leave the hot set (STANDARD §2). After the steps above, move to
`_archive/` under their own folder:

- a Backlog item at `status: done` **whose audit line is written**;
- an Issue at `status: archived`;
- a Proposal or Decision whose chain has completed and whose Backlog item is done.

```bash
git mv docs/23_backlog/BACKLOG-NNN-slug.md docs/23_backlog/_archive/
```

Use `git mv` so history follows. Nothing else changes: ids are unaffected because
file names are not reference keys (STANDARD §3), the validator still checks these
files in full, and they still appear in `INDEX.md` with an `_archive/` prefix.

**Never archive anything in layer 1.** Layer 1 is state, not history — a component
that no longer exists is removed by a Decision, not filed away. And never archive a
Backlog item at `done` that has no audit line; write the line first, or the trace is
lost in the folder that gets read least.

If nothing qualifies, say so in one line and move on.

## Step 7 — Validate and report

Run the validator again — it is fast, read-only, and this run covers what the sync
itself changed:

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

Fix only violations **introduced by this sync**; pre-existing ones belong to the
report.

Then regenerate the read models so they reflect the reconciled state:

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" "$(pwd)"
```

**This is no longer optional, and it is not only about the HTML.** The same command
writes `docs/INDEX.md`, which Step 2 and `brief` both read *instead of* the folders.
A sync that creates an Issue without regenerating leaves an index that omits it —
and a stale index is worse than no index, because the next agent trusts it. If the
script exits 3 (`python3` missing), say plainly that `docs/INDEX.md` is now stale and
that skills must fall back to reading the folders until it is regenerated.

Then summarize:
- **Updated**: backlog statuses changed, audit lines appended, amendments
  applied, `verified_at` moved forward, read models regenerated.
- **Created**: retroactive Issues (+ fast-lane Backlog items).
- **Archived**: what moved to `_archive/`, and how many documents that takes out of
  the folders skills read.
- **Architecture drift**: what Step 5 found — separating what the validator's
  `[anchor]` / `[stale]` lines proved from what you concluded by reading code — and
  the Issues opened for it.
- **Needs your decision**: full-lane work without a Decision, ambiguous mappings
  between work and Backlog items, unresolved validator failures. Ask — never guess.
