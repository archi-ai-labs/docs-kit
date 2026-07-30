---
name: docs-sync
description: Reconcile docs/ with what the current session actually did — update Backlog statuses, append audit entries, create retroactive Issues, apply pending Architecture amendments. Use only when the user runs /docs-kit:docs-sync or explicitly asks to sync/update the project docs after work.
---

# docs-sync — reconcile docs/ with this session's work

This is the **writing** skill of docs-kit. It runs inside the session that did
the work, because that session has the context. Ground rules come from the
model (STANDARD.md at the plugin root; digest in `docs/README.md`):

- `docs/92_audit/` is **append-only**: add lines at the end of the log file,
  never edit, reorder, or delete existing lines.
- `docs/02_architecture/` may be touched **only** via the approved-Decision path
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

For each piece of completed work with no matching Backlog item, create
`docs/20_issues/ISSUE-NNN-<slug>.md` with the required frontmatter
(`id, description, why, lane, status`), body noting **"Created retroactively by
docs-sync — the work was done before this Issue existed."**
- Lane by the two-question test (Architecture doc modified? revert > 1 day?).
- Fast lane → also create the Backlog item (`source_ref` = the Issue,
  `status: done`) and its audit line, so traceability is complete.
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

## Step 5 — Validate and report

Run the validator (resolve the plugin root as in docs-init Step 0):

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

Fix only violations **introduced by this sync**; pre-existing ones belong to the
report. Then summarize:
- **Updated**: backlog statuses changed, audit lines appended, amendments applied.
- **Created**: retroactive Issues (+ fast-lane Backlog items).
- **Needs your decision**: full-lane work without a Decision, ambiguous mappings
  between work and Backlog items, unresolved validator failures. Ask — never guess.
