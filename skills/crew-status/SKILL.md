---
name: crew-status
description: Read-only crew board — open worktrees vs tickets, held locks, and the three pacing signals, straight from scripts/crew status. Never edits anything.
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

- **worktrees** — each line is a ticket mid-flight. An `orphan` flag is
  steward work: a tree whose ticket is `done` (or missing) should be removed;
  a `note:` about an in-progress ticket without a tree means someone closed a
  laptop mid-ticket.
- **locks** — who holds which shared resource and for how long. A lock held
  for hours with no matching activity is usually a forgotten `release`.
- **pacing** — the three signals of EXECUTION §5, each mapping to exactly one
  action: rig idle → a heavy ticket may start; wait over budget → drop one
  heavy session; past the reader's ceiling → take nothing more, even light.

The thresholds are per-repo config, not truths — if the user questions them,
point at `.claude/crew/setup.md`, which explains how to re-derive both from
`log.tsv`.

Change nothing on disk, acquire no locks, remove no worktrees — name what
should happen and whose hat it belongs to.
