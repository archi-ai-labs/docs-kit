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

Read frontmatter of `docs/23_backlog/*.md`. For each item whose work happened
this session:
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

Read `components` and `data_flow` from `docs/02_architecture/architecture.md`
and the ```` ```flow ```` blocks in `docs/01_products/*.md`, then check them
against what this session actually touched:

- a component whose backticked path **no longer exists**, or moved;
- a new component-sized thing added this session (a new service, datastore,
  queue, or scheduled worker) that is absent from `components`;
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

## Step 6 — Validate and report

Run the validator (resolve the plugin root as in docs-init Step 0):

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

Fix only violations **introduced by this sync**; pre-existing ones belong to the
report.

Then refresh the generated HTML views so they reflect the reconciled state:

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" "$(pwd)"
```

(Skip silently if `docs/index.html` does not exist and the user never asked for
HTML views; if the script exits 3 — `python3` missing — mention it and move on.)

Then summarize:
- **Updated**: backlog statuses changed, audit lines appended, amendments
  applied, HTML views refreshed.
- **Created**: retroactive Issues (+ fast-lane Backlog items).
- **Architecture drift**: what Step 5 found, and the Issues opened for it.
- **Needs your decision**: full-lane work without a Decision, ambiguous mappings
  between work and Backlog items, unresolved validator failures. Ask — never guess.
