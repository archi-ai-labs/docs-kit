# Issue capture — the mechanics shared by `brief` and `docs-sync`

Two skills create Issues, from opposite directions:

| Skill | Direction | When |
|---|---|---|
| `brief` | forward | before the work — STANDARD §6, "create an Issue before writing code" |
| `docs-sync` | retroactive | after the work — reconciling what a session actually did |

The direction differs; the mechanics do not. They live here so the two cannot
drift apart.

**This file is procedure, not contract.** `STANDARD.md` at the plugin root is
the contract — the frontmatter fields, the enums, the lane rule all live there.
This file says *how to carry it out*; STANDARD says *what is required*. Never
copy a table out of STANDARD into this file: two copies drift, and then nobody
knows which is authoritative.

## Allocating an id

Next number for a type = highest existing number of that type + 1, zero-padded
to three digits:

```bash
grep -rh '^id:' docs/
```

Never renumber an existing id. The `-000` ids belong to the example chain
shipped by docs-init — real documents start one above the highest **real** id,
so a repo that still has its examples starts at `001` regardless.

## Naming the file

`ISSUE-NNN-<slug>.md` under `docs/20_issues/`, `BACKLOG-NNN-<slug>.md` under
`docs/23_backlog/`. The slug is lowercase ASCII with hyphens — a Vietnamese
title still gets an ASCII file name (STANDARD §11). File names are never
reference keys (STANDARD §3), so a clumsy slug is cosmetic, never a broken link.

## Filling the frontmatter

Required fields are in STANDARD §4 — read them there, do not work from memory.
The fields whose *content* takes judgment:

| Field | What it has to say |
|---|---|
| `description` | what this is about, one line — the work, not the symptom |
| `why` | why it is worth doing; a `why` that restates `description` is not filled in |
| `lane` | the outcome of the lane test below, never a guess |
| `status` | see the routing table |

`description` and `why` are explanation, so STANDARD §11 applies: they are
written in the language the repo's other docs use, with English domain terms
left bare inside the sentence.

## The lane test

STANDARD §5, two questions. **Any "yes" → FULL. Both "no" → FAST.**

1. Does this change modify the Architecture doc?
2. If it turns out wrong, would reverting take more than 1 day?

Ask them about the work, not about the size of the diff. A three-line change to
a schema is full lane; a thousand-line change to a test helper is not.

## Routing after the lane test

| Lane | Do |
|---|---|
| FAST | Create the Backlog item, `source_ref` = the Issue's id. Then set the Issue to `status: promoted`. |
| FULL | Leave the Issue at `status: open`. Stop there — the Proposal is the user's call. |

The Backlog item's `status`, and whether an audit line goes with it, depend on
which caller you are:

| Caller | Backlog `status` | Audit line |
|---|---|---|
| `brief` — work has not started | `open` | none |
| `docs-sync` — work already finished | `done` | one, appended |

**Why the forward path writes no audit line:** `92_audit/` records events that
happened. Work that is about to start has not happened. `docs-sync` appends the
line when the item flips to `done` — writing one here would log the same work
twice, and the second line would be the one that is true.

## The line neither caller crosses

**Never create a Decision, and never write a Proposal that has already picked
its winner.** `decided_by` is a human field; an agent filling it is fabricating
an approval nobody gave. When the chain needs a Decision that does not exist:
create the Issue, stop, and tell the user.

## Ids in text that an agent reads

The Stop hook marks a session "engaged" with the docs workflow when the
transcript mentions a concrete id (`ID_RE` in `scripts/hook_stop_scan.py`).
Skill files and this file are loaded into that transcript, so a literal id with
digits sitting in instructional text silences the hook in **every** session,
permanently.

In prose and examples — here, in skills, in reports — write `ISSUE-NNN`,
`DECISION-NNN`, `BACKLOG-NNN`. Digits belong only in files under `docs/`.
