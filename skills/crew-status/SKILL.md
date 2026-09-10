---
name: crew-status
description: Read-only crew board — executors vs tickets, held locks, and the three pacing signals, straight from scripts/crew status. Never edits anything.
disable-model-invocation: true
---

# crew-status — three answers, read from the traces

You are a **wrapper around `scripts/crew status`, nothing more** — the same
contract docs-check has with the validator: report what the script said, add
nothing, fix nothing.

## Step 1 — Run

```bash
bash scripts/crew status
```

If `scripts/crew` is missing or it answers "the crew layer is off", say so and
point to `/docs-kit:crew-init`. That is not an error to work around.

## Step 2 — Relay, then interpret

Quote the script's output, then read it back in plain language:

- **executors** — three states, all read off git: `idle` (detached, can take a
  ticket), `processing` (holds the ticket's branch), `finishing` (a commit on it
  already carries the `Closes:` trailer, so the work is declared done and only
  the merge is missing — that one has an action, `crew done`). An `orphan` flag
  is steward work: an executor still holding a branch whose ticket is `done` or
  missing should be parked. A `note:` about an in-progress ticket no executor
  holds means someone closed a laptop mid-ticket. A `pre-pool worktree` note is
  a `-b<nnn>` tree from before 0.31.0: land it, then remove it. The board reads
  git and not sessions, so `idle` means no ticket is taken — it does not prove
  a session is open, or that one is not.
- **locks** — who holds which shared resource and for how long. A lock held
  for hours with no matching activity is usually a forgotten `release`.
- **pacing** — the three signals of EXECUTION §5, each mapping to exactly one
  action: rig idle → a heavy ticket may start; wait over budget → drop one
  heavy session; every executor busy → the next ticket will grow the pool, so
  land one if you would rather it did not; past the reader's ceiling → land
  something before starting more, and shrink the pool once the burst ends
  (`crew executor prune`, which only ever touches idle trees).

- **direction** — two lines about the plan, both derived from git and `docs/`.
  `roadmap Now` compares the ids in the roadmap's `## Now` column against the
  Backlog: `done` counts cited tickets that are finished or missing, and a
  `not listed` line names open tickets that no column mentions. `report` says
  whether this ISO week has a file under `docs/92_audit/reports/`; `none due`
  means the window holds no landed ticket, so nobody owes one. Both arrows are
  navigator work — sync the column, or `scripts/crew report --write`. The whole
  block is absent when `navigator` sits in `roles_absent`, which is a declared
  choice rather than a fault, and the `role ... declared absent` note is its trace.

The thresholds are per-repo config, not truths — if the user questions them,
point at `.claude/crew/setup.md`, which explains how to re-derive both from
`log.tsv`.

Change nothing on disk, acquire no locks, add or remove no executors — name
what should happen and whose hat it belongs to.
