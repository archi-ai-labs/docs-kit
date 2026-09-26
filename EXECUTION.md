# docs-kit EXECUTION — the crew layer

This file is the **source of truth for how approved work runs**: from a Backlog
item to a merge on the dev branch, whether one session does the work or seven do
it in parallel. `STANDARD.md` governs what the documents say and how they change;
this file governs who does the work, where it happens, and what may run at the
same time. On document shape, STANDARD wins; on process, this file wins.

Every crew script, hook, template and skill conforms to this document, the same
way the validator conforms to STANDARD §4.

**Provenance.** The numbers below were measured on one real repo that ran
docs-kit with 5–7 parallel Claude Code sessions over 3 days. None are estimates.
Keep the numbers when copying rules elsewhere — a rule without its number reads
as an opinion. Where a number rests on one data point, it says so.

Unlike the model in STANDARD ("fixed — do not add stages"), this layer is still
learning. That is why it is a separate file: the two documents freeze at
different speeds.

## 1. Unit of work — one Backlog item, one token

The unit of work is the **Backlog item** (STANDARD §4). Crew adds no second
ticket system; it adds places for the same id to appear. One number reaches all
five, verbatim:

| What | Form | Example |
|---|---|---|
| Ticket | `BACKLOG-nnn` | `BACKLOG-157` |
| Branch | `work/b<nnn>` | `work/b157` |
| Lock owner | full id | `crew lock acquire e2e-harness 157` → owner `BACKLOG-157` |
| Executor tree | `../<repo>-e<k>` | `../myapp-e1` |
| Session name | `<repo> · executor · b<nnn> · [<subject> ·] [<first>→<last> ·] <e<k>\|main> · <state>` | `myapp · executor · b157 · d009 · e1 · processing` |

`<nnn>` is the zero-padded number exactly as it appears in `id:` — `crew`
normalizes `crew new 42` to `b042`.

Two addresses, and one thing joins them. The ticket number reaches the ticket,
its branch and its locks; the executor index reaches the tree and the session
that lives in it. What pins a ticket to an executor is **the branch that
executor has checked out**: git already stores it, git refuses to check one
branch out in two trees, and no file can disagree with it. `crew status` reads
that pin; nothing writes it. The session title is read off the same three
things — place, ticket, trailer — so it answers "where, which ticket, how far
along" without opening the board, and it cannot drift from what git says. Since
0.42.0 it also carries the ticket's **subject** — the document its `source_ref`
names, as a token (`d009` is DECISION-009, `i020` is ISSUE-020) — which is the
way back from a ticket to the planner working on it (§3). The
place is `e<k>` for a pooled executor and **`main` for a fast-pair session**,
which skips the worktree and the branch but is still a session of its own. There
is deliberately **no idle title** and no ticketless one: an executor session
holds exactly one ticket at a time, and without one there is nothing to name. An executor holding no ticket sits at a detached
HEAD on the dev branch, because "on dev" is the one thing a second worktree may
not be.

Before 0.31.0 the tree carried the ticket number too, and was built and
destroyed once per ticket. The cost that ended that, from the origin repo's own
log: four trees for fifteen tickets, **49 seconds** of provisioning in total —
small there, but it is thrown away and re-paid every ticket, and it grows with
the repo. A tree is the part of a ticket that is worth reusing; the branch and
the session are not.

**Not every job is a ticket.** A ticket costs a branch, a merge and an executor
slot for as long as it runs, so anything cheaper than that is done where it is
found. Bookkeeping on Layer 2 documents
(archiving or closing an Issue, correcting a status, a typo in a ticket) is not
delegated work: whoever notices does it with the audit line, or it rides along
with the ticket that produced it. A whole ticket spent archiving one Issue
trades the full setup cost for a single file edit. The boundary is code: work
that touches code is a ticket even at one line, and a one-file ticket is
`fast-pair` (§2), not "not a ticket". Direction work — a survey, a plan, a
periodic report — is not a ticket either: it is the navigator's file under
`92_audit/reports/` (§3), and the measured cost of routing it through the Backlog
instead is `BACKLOG-017`.

**The ticket exists in the main tree before its branch does.** `crew new`
refuses to open a branch for an id it cannot find under `docs/23_backlog/`.
This is not ceremony: id allocation is read-then-write ("highest + 1", STANDARD
§3), and a worktree only sees its own `docs/`, so two worktrees allocating ids
collide deterministically — git even merges the collision cleanly because the
file names differ, and the duplicate surfaces only at the next validator run.
Allocating on the main tree before any worktree exists is what makes the
collision impossible instead of unlikely. It also makes the Backlog the single
intake: **no ticket, no branch.**

**One ticket = one branch; one session per chain, carried to `done`.** A ticket
nobody chained is a chain of one, so for most work this still reads "one ticket,
one session". 0.31.0 made the *tree* outlive the ticket, and 0.41.0 lets the
*session* outlive it too, but only along a chain the planner wrote down and
only for a session that was given it: `crew new <first> --chain` (0.41.2). A
session is born for a ticket, titled `processing`, and ends `finished`; its
title always names exactly one ticket, the one its tree holds now. The
measurement that bought the per-ticket half of this rule:
one owner request ("fix the demo top-up") cut across 4 technical roles took
**15h32** wall-clock of which **~87 minutes** had commits, and the owner was
told "done" 4 separate times. The longest stretch was **7h18 of finished work sitting unmerged on a
branch** — which happened 3 times in 2 days. Cutting tickets by request instead
of by technical layer is the fix; the first two tickets run under this model
closed in **15 and 41 minutes**.

**A chain is tickets that cannot run side by side, and the planner records it
on the later ticket** as `after_ref: BACKLOG-<nnn>`. Measured on the repo that
reported the gap (GitHub issue #4: about 330 Backlog items, a pool of 6
executors): a run of 8 tickets, each moving a route file into a folder tree
the one before it created, so ticket N+1 edits the mount file ticket N built.
One session per ticket meant **8 hand-offs**, each a session the owner starts
by hand plus a re-read of the context. The owner split the run into two lanes
of 5 and 3 and asked one executor to carry each, and then no surface said so:
the title and `crew status` each named one ticket, and the order of the chain
lived only in a chat message between two sessions. A hand-typed title such as
`b332-336` went red on every later ticket, because `crew name` computes one
number.

The field sits on the ticket that has the dependency, the same direction as
every other `*_ref`, so the validator's ref check (STANDARD §3) already
resolves it and nothing new checks it. The order is not a flag on `crew new`:
that would keep it in `../<repo>-crew/`, which is never committed and is
written by the executor, not by the planner who decided it.

**Who carries a chain IS a flag, because it is a fact about a session.**
Measured 2026-09-24 on 0.41.0, three real executor sessions on one
`332→333→334` chain: the two given the planner's chain prompt carried it end to
end, but the one given the ordinary one-ticket prompt for 332 stopped after
`crew done 332`, rightly, since its prompt put 333 out of scope. `crew done`,
reading only `after_ref`, had already switched its tree to `work/b333`, so e1
sat on a branch nobody was working, and the board read `e1 on 333 ·
processing`, word for word what a live session looks like. Whether a session
carries the chain is decided by the prompt it got, so the session says so once,
`crew new <first> --chain`, and `crew` logs it on that ticket's `NEW` line in
`../<repo>-crew/log.tsv`. Each handoff's own `NEW` line carries it on, so the
flag is never repeated. Without it `crew done` parks exactly as it does for a
lone ticket. With both in place:

| Command | What the chain changes |
|---|---|
| `crew new <nnn> [--chain]` | refuses with `[new:after]` until the predecessor has landed on the dev branch (closer on dev, or doc `done`), and says whether the session holding the predecessor carries the chain; `--chain` makes this session carry it from `<nnn>` on |
| `crew done <nnn>` | for a session carrying the chain, when a ticket runs after this one, the tree goes **straight** from `work/b<this>` to `work/b<next>`, cut from the dev branch that now holds this merge, and prints the chain's progress line; `--park` ends the chain session here instead. A session that opened the ticket without `--chain` gets a park tagged `[done:alone]` that names `scripts/crew new <next> --chain`. The carrying session's last `crew done` prints the tickets it carried, each with the sha that closed it and its logged size, for the final report |
| `crew name executor` | adds `<first>→<last> ·` after the subject: `myapp · executor · b334 · d009 · 332→336 · e1 · processing` |
| `crew status` | a `chains:` block: what landed, who holds which ticket (`(this ticket only)` when that session does not carry the chain), what is queued, and an arrow when no session carries a chain that has a ticket ready, with `--chain` when more than one ticket is left |
| `crew wait <nnn> [<nnn>…]` (0.43.0) | blocks until every ticket named has landed, by the same `landed` test `crew new` gates on, and no tree still holds its branch; then prints each ticket whose `after_ref` names one of them, with the tree the chain's session took it into or the command that opens it. Polls the local dev branch every 30s, with no timeout |

**The chain's executor never reads `idle` between two of its tickets.** A parked
tree is a free tree (§5: detached and clean is the whole test), and a free tree
is what the next `crew new` takes. Parking after one ticket and letting the
session run `crew new` for the next would open exactly that window, and a
second session would take the tree the chain session is sitting in. So the
switch happens inside `crew done`, under the same `assign.lock` mutex `crew new`
claims under, and never passes through a detached HEAD; `crew_test.sh` reads
the executor's own reflog to prove it, because park-then-switch ends in the
same state and only the move itself differs. The pin is still the checked-out
branch, and there is no reservation file.

One predecessor per ticket makes a chain a line and a fork a tree. At a fork
`crew done` continues into the lowest-numbered successor not yet done and
names the others, each of which needs a session of its own. A `fast-pair`
successor runs in the main tree by definition, so the tree is parked and the
session carries on from there, taking the next executor ticket with
`crew new <nnn> --chain`. One ceiling, stated: a leftover file that
keeps the tree on the old branch also stops the handoff, so after clearing it
the session runs `crew new <next> --chain` from inside that tree, which
`crew new` prefers over any other free one. (0.41.0 stated a second one — each ticket's
close-out left uncommitted in the main tree, so the next `crew done` in the
chain met check 2 — and 0.41.1 removed it: `crew done` now commits its own
close-out, §6.)

**Opening what a landed ticket unblocks is `crew wait`.** Reported in GitHub
issue #5, which calls a chain a "lane" (in this kit a lane is STANDARD §5's
fast/full choice): a planner ran five chains, three of them forking from one
net ticket (an end-to-end tour of every screen), and one final ticket after
those three. The chains after the net ticket got no chip until it merged, and
the planner watched for that with a hand-written
`until git fetch …; git log origin/dev --grep='Closes: …'` loop in its own
session. `crew wait` is that loop as a command. It reads the local dev
branch, because every session runs on one machine and `crew done`
fast-forwards the main tree's dev branch before it pushes. Run in the
background, it tells a planner the moment the fork's other chains can be opened,
and it prints the command for each.

It waits out one more window than the loop did. The closer reaches the dev
branch at step 5 of `crew done`, and the tree moves on to the chain's next
ticket only after the close-out and the push (§6). Exiting at the closer would
print that next ticket as ready inside the window, and a chip opened for it
would race the session carrying the chain into it. So `crew wait` also waits
until no tree holds `work/b<nnn>`; a closer merged by hand into a tree nobody
releases is waited on the same way, and the command says so once.

**A ticket with more than one predecessor carries no `after_ref`.** The field
holds one ticket, and pointing it at one of the chains is worse than leaving it
off: `crew new` would gate on that chain alone, and the session carrying that
chain would be handed the ticket by its last `crew done` while the other chains
were still running. The planner leaves the field empty, runs
`crew wait <last of each chain>…` in the background, and opens the ticket when
it exits. A join in the field itself is left for a design pass: with three
predecessors carried by three sessions, which session carries on into the join,
and where the title's `first→last` walks back to, are both open.

## 2. Execution levels — where the work happens

STANDARD §5's lane decides the **document path** (`lane: fast | full` — the enum
does not change). The execution level decides the **working location**. Fast
lane splits in two by size:

| Level | Lane | Branch | Tree | Entry conditions |
|---|---|---|---|---|
| `fast-pair` | fast | dev branch directly | main tree, own session | ≤ 1 file · plain revert undoes it · touches no contract |
| `fast` | fast | `work/b<nnn>` | a free executor | fast lane, but bigger than that |
| `full` | full | `work/b<nnn>` | a free executor | full lane (Decision exists) |

All three levels have a ticket **and a session**. `fast-pair` is not "skip the
ticket", and not "skip the session" either — it is *ticket + session + dev
branch*, skipping only the worktree and the work branch. What it saves is one merge round and one executor slot,
which is most of the lifetime of a one-line fix.

The level may be recorded on the Backlog item as an optional `execution:` field
(`fast-pair | fast | full`). The validator does not check it in 0.26.0; `crew
new` reads it and refuses to take an executor for a `fast-pair` item.

**fast-pair discipline (defensive, because the collision is real):** the merge
procedure's cleanliness check (§6, check 2) requires the main tree's status to
be empty, so an open fast-pair edit blocks every `crew done` in flight, and each
fast-pair commit moves the dev branch under a pending `--ff-only`. Therefore:

- a fast-pair edit is **committed in the same working bout** — never left
  sitting in the main tree;
- `crew done`, on finding the main tree dirty, **names the dirty files** instead
  of failing blind, so the blocked executor knows who to ping;
- `crew done` retries its merge cycle (merge dev → re-test → `--ff-only`) up to
  2 times when the dev branch moved underneath it, then stops and says so.

**A checkout is not a working environment, and the pool pays for that once.**
Dep dirs, nested harness repos and env files are gitignored, so a fresh tree
lacks them; `crew executor add` puts them back from config — `copy` for mutable
payload (APFS clonefile where the filesystem offers it, so gigabytes cost
seconds), `link` for strictly read-only shares, `setup_cmd` for whatever needs a
command — and logs the total as a `SETUP` line against the executor, not against
a ticket.

The saving is that a landed ticket leaves its dependencies behind for the next
one, and that is also the new hazard: a ticket that moved a lockfile would
otherwise leave the next ticket testing against the wrong tree. So `crew new`
re-runs `setup_cmd` when any `resetup_when` file differs from the one this
executor was last set up with, and skips it when none does. The default list
covers the usual lockfiles; the stored key is a cache key and never a source of
truth about who holds what.

One boundary is a rule, not a missing feature: **a ticket that edits a nested
repo belongs to that repo's own crew** — an executor cannot isolate inner-repo
edits, and an edit made inside a provisioned copy is not on the branch.

## 3. Roles — cut by work, not by technical layer

Six hats plus one procedure. **Hats, not headcount**: a solo repo wears all
six and loses nothing; the constraints below only start to bind when hats sit
on different sessions. A hat can also be *not yet worn*: `crew-init` refuses
to stamp a role no evidence supports (§9 `roles_absent`), and `crew status`
keeps naming the gap until someone wires it.

| Role | Does | The constraint that earns its keep |
|---|---|---|
| `planner` | measures the bug where it lives, writes the ticket, sets lane and level, assigns | **writes no code** |
| `executor` | one ticket – one tree – to `done`; n in parallel | merges its own work (§6) — waits for no reviewer |
| `tester` | acceptance + exploratory testing playing the customer | **patches nothing it finds** — findings become Issues (the STANDARD intake), planner triages them into Backlog |
| `devops` | holds the production branch, watches the running build | takes no code tickets |
| `steward` | builds/removes trees, keeps the status board, writes the rules | **assigns no work, receives no reports** |
| `navigator` | keeps `## Now` equal to the open Backlog, writes the weekly report and the monthly plan into `92_audit/reports/`, routes a change of direction through Proposal → Decision | **writes no Backlog item, takes no ticket** |
| `release.md` | promotion procedure dev → production | a procedure `devops` runs, not a seventh hat |

"Planner writes no code" is not tidiness — it is the only mechanism that
catches mis-graded tickets. Measured case: a ticket graded LIGHT ("one file,
under 50 lines") held the shared test rig for **871 seconds**, because the file
it touched changed how an ops tool behaves when the environment is broken. The
executor reporting that number back is what corrected the grading; if the grader
had been the fixer, the number reaches no one.

The tester constraint has its own number: one manual acceptance pass playing
the customer produced **12 findings while the automated suite stayed green**.
Findings enter as Issues so the intake stays single (§1) and the planner stays
the only writer of Backlog items.

**"Navigator writes no ticket" protects the same seam twice.** Forward, it keeps
the single intake: the planner stays the only writer of `23_backlog/`, so ids are
still allocated in one place and the roadmap cannot become a second ticket system.
Backward, it keeps the measurement honest — the hat that reports the drift must
not be the hat that can erase it by rewriting the ticket, which is the planner's
871-second rule read from the other end.

The gap it fills was invisible because nothing compared the two documents.
Measured on the origin repo 2026-09-10 (one repo, one day — one data point):
`00_roadmap/roadmap.md` had not changed in **10 days**, while **10** commits
carried a `Closes:` trailer, **29** audit lines cited a Backlog id and **5**
`DONE` lines landed in `log.tsv`. Its `## Now` column named 4 tickets, **4 of 4
already `done`** and archived, and **neither** of the 2 open tickets appeared in
any column. Not one check went red, because none existed. The planner hat was
worn throughout those ten days, which is what rules out folding this into the
planner: attention there is per ticket, and nobody reports drift against tickets
they cut themselves.

The second measurement is what fixes the boundary. `BACKLOG-017` on the same repo
is direction work — a market survey and a six-month roadmap — pushed through the
Backlog as a code ticket: `scope_files: 0`, three deliverables inside the
gitignored `briefs/`, and the ticket itself instructing the executor **not to
close it** because the owner has to approve the report first. That is a ticket the
ticket system cannot close, holding a slot in the intake, whose output dies with
the session. Under this hat the same work is a file in `92_audit/reports/` and a
refresh of `## Next`, and no ticket at all.

**The roadmap has one writer, and the report has one home.** `00_roadmap/roadmap.md`
belongs to the navigator the way `23_backlog/` belongs to the planner; the planner
*reads* `## Next` top-down to choose what to ticket and edits nothing. Reports go
to **`92_audit/reports/`** — a subfolder, and the subfolder is load-bearing:
`docs_close.py::audit_ids` reads every `*.md` **directly under** `92_audit/` and
treats any Backlog id it finds as a completion already recorded, so a report
sitting beside `LOG.md` and naming an open ticket would make that ticket close
with **no audit line and no message**. Reproduced on a fixture both ways before
this was written: flat gave `status -> done` alone, the subfolder gave
`status -> done, audit line`. The same trap survives in the `ref` column of
`LOG.md` itself, which is why a navigator's audit line cites the report's path
and never an open id. (The underlying containment check is worth narrowing on its
own; it is a defect of close-out, not of this hat, and it is not fixed here.)

**A hat is only worn if the session list shows it.** Every session title reads
`<repo> · <role> [· <task>]`: the project, then the hat, then what it is working
on. An executor's task is its ticket (§1); a hat working one ticket takes it as
`<repo> · tester · b157`; a subject planner takes its document,
`<repo> · planner · d009 <slug>`; a hat with nothing in hand stops at the role.
The repo leads so any session list sorts by project, and the fixed part leads
the optional one, so a hat with no task is the head of the same title with one.
The ticket keeps the §1 token verbatim — `b157`, the same string the worktree
and the branch carry. `crew name <role> [<nnn>|<subject>]` compares the running
session against that grammar and exits 1 when it does not match; `steward.md`
runs it as a hard first step, ahead of even read-only work.

Until 0.42.0 the role came last, behind a `crew/` prefix
(`myapp · e1 · b157 · processing · crew/executor`). The user reordered it to
project → role → task and dropped the prefix to win back the width, and the
ticket moved to the head of the task part because a list that cuts a long title
keeps its head: the ticket sits at characters 31–34 of
`long-wave-finder · executor · b015 · d009 · e1 · processing`, close to the 25–28
it had before. A title still in the old grammar is carried over by title-nag (§8).

**The subject is the way back to the planner.** Measured 2026-09-24 on four
repos: with several planners open, every one of them was titled
`<repo> · crew/planner`, and from a `b<nnn>` alone the user could not tell which
one to go back to. The link already existed in every ticket — `source_ref`, which
the validator already resolves — and nothing showed it. So the executor title
carries the source as a token, a planner working one subject carries the same
token plus the words its document's file name already holds
(`crew name planner d009` → `<repo> · planner · d009 co-vi-the-theo-von-hien-tai`),
and a token no planner wears means the general planner, `<repo> · planner`. The
words are read, not typed, and an id with no document behind it is refused.

Four other keys were considered and dropped:

| Key | Why not |
|---|---|
| a number per planner (`planner 1`, `planner 2`) | says nothing about the work; the user rejected it in as many words |
| the kind of work (`techdebt`, `hotfix`, `ft/<name>`) | the user's own first scheme, dropped by the user: it still does not say what the planner is doing |
| the app's parent link (`spawnedFrom`) | present on 40 of 40 chip-born executors, but it names the session that MADE the chip — with a coordinating planner making the chips, every executor points at the coordinator. It is also desktop-only and not readable from bash |
| a `planner:` field in the ticket | typed by hand, and it names a session, which ends, instead of the work, which does not |

A subject planner is worth opening only when its subject will produce more than
one ticket: across the same four repos, 53 tickets came from 49 source documents,
and only 3 of those produced more than one. Most Issues stay with the general
planner, so the list grows by a planner per big subject, not per ticket.

**Sidebar groups are a view, desktop only, and opt-in by the user's own
sidebar.** The desktop app files sessions under custom groups, and only the model
inside the app can move them — so `crew name … --group` prints the groups a
session belongs in, subject's first, project's second, and the role files say
what to do with them (`roles.md`, "Nhóm sidebar"). Three facts measured on the
user's own sidebar on 2026-09-24 set the rules:

- **Groups and the project view exclude each other.** Moving one session into a
  group switched the whole sidebar from "by project" to "custom groups", every
  ungrouped session fell into one bucket, and the user read it as "the others are
  all gone". So a session joins a group only if that group already exists, and
  the kit never creates a project group: the user who wants groups creates them,
  and their existence is the opt-in. Only a subject planner creates a group — its
  subject's — and only when its project group already exists.
- **Group order is creation order**, and no tool reorders groups, so a subject
  group created later lands at the bottom; the planner tells the user to drag it.
- **A chip-born session appeared inside its parent's group without anyone moving
  it** (one observation, BACKLOG-015 of long-wave-finder). The executor's own step
  still moves it, because one observation is not a contract, and because the
  parent that made the chip is not always the planner of the subject.

Moving a pinned session into a group unpins it, so a pinned session is left where
it is. The title and `crew status` stay the source of truth; a group is only how
the desktop shows them.

**It reads the session TITLE, and the difference is not cosmetic.** A session
carries two labels: a `name` in the live entry `~/.claude/sessions/<pid>.json`,
and a title that the session list displays. Renaming inside the desktop app
writes the title only; `/rename` in a terminal writes both. The first version of
this check read `name`, and four sessions renamed in the app — each correctly
named, each plainly readable in the sidebar — came back red. A check that fails
on the exact gesture it asks for is a check that gets switched off, so it now
reads the title: the last `{"type":"custom-title"}` record in the session
transcript, reached from the sessionId in the live entry.

**What the rule does not buy.** Titles are not unique, so nothing here prevents
two sessions from wearing one hat; it makes the hat visible, and a human reading
the list is what catches the duplicate. `steward.md` and `navigator.md` run the check today — the two hats
that write into the shared main tree; the other hats state their title and can
adopt it when someone measures a reason. Fail open holds as everywhere else in this kit — no session entry, no
transcript, no python3, and the check reports the expected title rather than
blocking the role.

**A steward session must state, in the request itself, when a rule change
expands its own authority.** This has happened (a steward wrote into its own
rules file that stewards build worktrees); the owner approved it, but nothing
had forced the disclosure. Nothing can — the rule is discipline, and it is
written here so silence reads as a violation rather than an oversight.

## 4. Shared state — `../<repo>-crew/`

Locks, the time log, and the gate log live in a sibling directory of the main
tree: `../<repo>-crew/`. It sits **outside every checkout on purpose** — a
worktree holds its own copy of every tracked file, so state kept inside the
repo would fork per worktree and no session would see another's locks, which is
the exact failure this directory exists to prevent. The origin repo ran 3 days
on this layout.

**Resolution is computed, never guessed:** the main tree is the first entry of
`git worktree list`, and the state dir is `<parent-of-main>/<basename>-crew`.
Every `crew` subcommand and both hooks resolve it this way, so the rule works
identically from the main tree and from any `-e<k>` executor.

Contents:

```
../<repo>-crew/
├── assign.lock/             # mkdir mutex, held only while an executor is claimed
├── keys/<repo>-e<k>         # cksum of the resetup_when files at last setup
├── locks/<resource>.lock    # owner id + ISO timestamp, one file per held lock
├── logs/                    # whole output of the repo's own commands, one file per run (§6)
├── log.tsv                  # append-only: ts · event · resource · ticket · seconds
└── gate.log                 # explain-gate fail-open trail (§8)
```

`log.tsv` events: `ACQUIRE` (seconds = time spent waiting), `RELEASE`
(seconds = time held), `WAIT` (a request that had to queue). The directory is
never committed anywhere; deleting it loses runtime state only.


**Check-then-write is not a claim, and both places that did it were wrong.**
Measured 2026-09-08, before the fix. Three concurrent `crew new` against a pool
of two: all three read the same free executor, the last `git switch` won, and in
**4 runs out of 5 only one ticket landed** while the second executor sat idle and
a branch was left held by nobody — a command that had already printed success had
its tree taken. Two concurrent `crew lock acquire` on one resource: **both
reported success in 5 runs out of 5**, while the file recorded a single owner, so
two sessions each believed they held the rig.

Both now use an atomic test-and-set from the portability floor: `crew new` wraps
"who is free" through "the branch is checked out" in a `mkdir` mutex
(`assign.lock`, bounded wait, released on every exit path including `die`), and
`crew lock acquire` makes the **write itself** the test via `O_EXCL` (`set -C`),
same file format as before. Provisioning stays outside the mutex — it can run for
minutes, and by then the tree already belongs to that ticket. Neither defect is
visible by reading the code, so `crew_test.sh` races both for real.

## 5. Locks and pacing — resources are locks, not roles

A shared test rig, a stable local environment, a staging database — usually one
of each exists. A role that owns them becomes a queue of people; a **named
lock** is a queue of tickets. Resources are declared in config (§9) with the
command patterns that tend to touch them:

```
crew lock acquire e2e-harness 157      # blocks or queues; logs wait time
crew lock release e2e-harness 157      # logs held time
```

Every ticket splits into a **local part** (typecheck, unit tests — parallel
without limit) and a **rig part** (e2e, staging — queued through the lock). The
rig part goes small and last. A ticket whose rig part outweighs its local part
is an ops ticket and queues separately — it does not set the pace for
executors.

**Pacing reads as three signals, not a formula.** `crew status` translates
`log.tsv` into:

| Signal | Reading | Action |
|---|---|---|
| Cumulative lock wait today = 0 | the rig is idle | taking another heavy ticket is fine |
| Cumulative lock wait today > 30 min | the lock is the bottleneck | drop one heavy session |
| Pool grew this session | a guessed size was too small | fine while the burst lasts; shrink after |
| Pool size > 4 | past the reader's ceiling | land something before starting more, even light |

**Executor state is derived, never stored.** `crew status` reads it off git, so
nothing can go stale and nothing has to be written down:

| State | How it is read | Means |
|---|---|---|
| `idle` | detached HEAD **and** nothing uncommitted | free; no ticket and therefore no session |
| `unclean` | detached HEAD but files uncommitted | holds no ticket, yet not free — clear it |
| `processing` | holds `work/b<nnn>`, or holds it with files uncommitted | a session is on that ticket |
| `finishing` | a commit carries `Closes: BACKLOG-<nnn>`, the tree is clean, and the close-out is not finished | declared complete, not landed yet |
| `finished` | that commit is reachable from the dev branch **and** the ticket reads `status: done` | nothing is left on this ticket |

"That commit" is one the branch made itself. A closer for the ticket that reached
the dev branch any other way is printed at the end of the row as
`bypass=<sha>` and does not move the state (0.42.2, §6).

**Uncommitted work is part of the state, not a column beside it (0.32.0).** Both
rows above that say "and" were measured on 2026-09-09, in one repo, from one
cause: the tree was read through its branch alone. With the trailer written and
one file still uncommitted, the board printed `finishing dirty=1` — two columns
contradicting each other — and `crew done` then ran to completion: the merge
landed, the ticket flipped to `status: done` with an audit line citing a sha,
and the file never left the executor. The same blindness at the other end of the
cycle: a tree parked by hand, which is exactly what `crew done` tells the
operator to do when its own park refuses, still carried the finished ticket's
file, read `idle`, and was handed to the next ticket — one ticket's work sitting
on another ticket's branch, one `git add -A` from being committed there.

`unclean` earns a word by the rule the other three obey: something acts on it.
Such a tree drops out of the pool, so `crew new` grows instead of taking it —
and without the word the pool would grow with no reason visible on the board.

The rule holds for an executor because an executor tree belongs to exactly one
ticket, so anything uncommitted in it is that ticket's. **It is deliberately not
applied to the main tree**, where a fast-pair session works: that tree is shared.
Other sessions' fast-pair edits sit there, and so does the close-out
`/docs-kit:docs-sync` writes for a fast-pair ticket, which it never commits.
(`crew done` stopped adding its own to that list in 0.41.1, by committing its
close-out, §6.) Reading dirtiness as "still working" there would pin every
fast-pair session at `processing` whenever anyone else left a file open. The main
tree has its own guard instead, check 2 in §6.

A fast-pair session reads the same two states, only from a different place: it
has no branch of its own, so the trailer is looked for on the dev branch itself.

The last three are also the session's own states, and the title carries
whichever holds — the session is born `processing` and ends `finished`. Only
states something **acts on** get a word. `finishing` earns its own because
the origin repo measured finished work sitting unmerged for **7h18** with no
board saying so, and the action is "run `crew done`". A state for "taken
but not started" was considered and dropped: it is a window, not a condition,
and nothing behaves differently in it. Provisioning is likewise not a state —
it happens inside `crew new` and is skipped entirely unless a lockfile moved.

**`finished` closes the same gap at the other end (0.39.0).** Measured
2026-09-12 on a fixture repo: the moment `crew done` fast-forwarded the merge,
the board and the title fell **back** from `finishing` to `processing` — the
only test was the range `<dev>..work/b<nnn>`, which a fast-forward empties, so
work already sitting on the dev branch was reported as a session still editing.
Then `crew done` parked the tree, `crew name` exited 1 because a parked tree
holds no branch, and the title-nag hook — silent on any non-zero exit — left
the session at `finishing` for the rest of its life. A session list full of
`finishing` cannot say which rows still need the merge, which is the one
distinction `finishing` was invented to make. `finished` earns its word by the
same rule as the others: its action is "close the session, park the tree", and
nothing else asks for that.

It takes **both** halves, because a close-out is both halves (STANDARD §6.1):
the closer reachable from the dev branch, and the ticket reading `status: done`
with its audit line. `crew done` writes them in that order and only `note`s when
docs_close cannot be reached, which is every plain terminal with no
`CLAUDE_PLUGIN_ROOT` (ISSUE-014). The gap between them therefore happens in
practice, and it keeps reading `finishing` — correctly, since something is
still owed. What changes there is only the action: `crew done` cannot be re-run
once the tree is parked, so the remaining half is written by
`/docs-kit:docs-sync`, and `crew name` says exactly that instead of repeating
its take-a-ticket line. A separate word for that gap was considered and dropped:
the action differs, but the reading — "this ticket still owes something" — does
not, and five words for one ticket is past what a board can be read at a glance.

The uncommitted-work test stays **first**, ahead of both. A merge does not make
somebody's unlanded file less important, and that file is the one thing in an
executor tree that must never go invisible.

Two ceilings, stated rather than papered over. The `dirty=` count excludes
crew's own provisioned payload, because some of it cannot be gitignored at all
— a `dir/` rule does not match a symlink — and counting it would report a fresh
executor as having uncommitted work. And the board reads git, not sessions: it
cannot tell an executor whose session is open from one whose task chip nobody
has clicked. That is not a gap, because `crew new` is run BY the executor
session as its own first step, so an unclicked chip means no ticket was taken
and the executor honestly reads `idle`.

Heavy ticket (needs a lock) = 1 slot; light ticket = 0 slots; **one slot per
resource** — the rig only exists once, and a second executor does not create a
second rig. The 4-session ceiling has a different reason: usually one human
reads the results. It is a **warning, never a refusal**: a pool size is a guess,
so `crew new` with nothing free grows the pool by one and says so, rather than
blocking a ticket on a number somebody picked in advance. Growth is logged as a
`GROW` line. Shrinking back is the deliberate act, and it is **one** command
because otherwise an automatic ratchet only ever turns one way:
`crew executor prune [floor]` removes the idle trees down to a floor (default 2)
and keeps every executor that still holds a branch, naming it. `crew executor rm
<k>` removes exactly one, and refuses while that one holds a branch. 30 minutes is a starting point to
tune per repo, not a constant; the raw log is kept precisely so the thresholds
can be re-derived.

*Appendix — where the thresholds come from.* `p` = fraction of a ticket's
lifetime spent holding a lock; `N_max = 1/p`. The origin repo measured `p` on
its first two ops-queue tickets: **0.78** and **0.36**. Honesty note: at
`p = 0.78` the rig part outweighs the local part, which by this section's own
definition makes it an ops ticket that queues separately — so executor-mix `p`
is still unmeasured, and the first two tickets under the crew model (15 and 41
minutes) touched no lock at all. That is why operators get the three signals
above rather than a formula fed by the wrong queue's data.

## 6. `crew done` — the merge procedure is a command, not prose

The origin repo's meta-lesson, measured at **5 bites in one day**: *a string
match is not a measurement* — and a procedure kept as prose gets re-typed from
memory, where the two middle checks are the first thing to fall out. So the
merge procedure lives in one command, and sessions **run it, never re-type it**:

```
crew done 157
```

0. **Check 0:** the executor's own tree owns nothing uncommitted. Step 2 tests
   exactly what is about to land, and a dirty tree means what lands is not what
   the session has. This check already existed at the very end of the command,
   as the park refusal; measured 2026-09-09, that is too late — by then the
   merge had happened and the ticket read `status: done`. Same test, moved in
   front of the merge. Crew's own provisioned payload never counts.
1. In the executor holding `work/b157`: `git merge <dev-branch>` — conflicts
   are resolved there, never on the main tree.
2. Typecheck + test commands from config — testing exactly what is about to
   land, post-merge. Their whole output goes to
   `../<repo>-crew/logs/b<nnn>-typecheck.log` and `…-test.log`; the command
   prints the path, and on a pass the runner's last 8 lines (its counts), on a
   failure the last 40. `setup_cmd` is logged the same way.
3. **Check 1:** the main tree currently has the dev branch checked out
   (`git -C <main> symbolic-ref`). A merge lands on whatever branch the main
   tree holds, not on the branch you assume.
4. **Check 2:** the main tree's `status --porcelain` is empty; if not, the
   dirty files are listed by name (see §2 fast-pair). Known limit, stated
   rather than papered over: a clean tree does **not** mean nobody is reading
   it mid-review.

**Both of these checks are now on the board.** `crew status` opens with the main
tree's branch, whether that is the dev branch, and its uncommitted count, so the
two ways a merge gets refused are visible before a ticket is in flight rather
than at the moment one tries to land. It counts with plain `status --porcelain`,
the same way check 2 does and deliberately not the filtered `own_files()` an
executor row uses — filtering there would report a clean tree and then let the
merge refuse, which is worse than not reporting. It also prints how far the main
tree is from dev: against the remote when it is on dev, against dev itself when
it is on anything else, because "in sync" is a different question in each case.
5. `git -C <main> merge --ff-only work/b157`. If the dev branch moved: back to
   step 1, at most twice.
6. Close-out: if a commit on the branch carries `Closes: BACKLOG-NNN`, run
   `docs_close` (STANDARD §6.1) so `status: done` and the audit line cite the
   sha, then **commit exactly what it wrote** on the dev branch as
   `docs: close-out BACKLOG-NNN`; otherwise print the reminder and leave the
   flip to `docs-sync`. Then push the dev branch and the work branch (skipped with
   a note when no remote exists), so the remote gets the merge and the close-out
   together. Release any locks still held by the ticket. Then, when a ticket names this one in its
   `after_ref:` and the session carries the chain (`crew new --chain`, §1),
   **hand the tree on**: switch it straight to that ticket's branch,
   cut from the dev branch that now holds this merge, so the chain's executor
   never reads free (§1). Otherwise, or with `--park`, **park** the executor —
   detach it back onto the dev branch, which is what makes it free again. Its
   provisioned payload stays; any other uncommitted file keeps the executor on
   the branch and is named, exactly as the old teardown refused to delete it.

**The close-out is committed, and only the close-out (0.41.1).** Before, the
status flip and the audit line stayed uncommitted in the main tree, so the next
`crew done` anywhere died at check 2 naming exactly those two files, and its own
hint guessed "an open fast-pair edit?". Reproduced on 2026-09-24 with two tickets
back to back. Two parallel executors met it already, and a chain session (§1) met
it on every ticket after the first. The push also ran before the close-out, so
even a close-out committed by hand reached the remote one ticket late, riding the
next ticket's push, and the last one of a run not at all. What is committed is measured and
bounded. It is measured as the paths that became dirty while `docs_close` ran,
because the tree is shared and a fast-pair session can start an edit after
check 2. It is bounded to a Backlog doc, `92_audit/LOG.md`, and `INDEX.md` and
`MAP.tsv` (0.42.4, below), the only files `docs_close --apply --refresh` can write, so
nothing else is ever swept in under the close-out's name. A file that was already dirty when the close-out started holds
someone else's edit, so it stays out and is named with `[done:closeout]`. A
commit the repo's own pre-commit hook refuses is reported with the same tag and
the files, never bypassed, and it does not fail a merge that has already landed.
The commit carries no `Closes:` trailer, because a second closer for the same
ticket would force every reader of closers to decide which one counts.

**The close-out carries the index, and the gates speak in a few lines
(0.42.4).** Both measured on 2026-09-26 in real executor sessions. First, the
close-out committed the status and the audit line but left `docs/INDEX.md` and
`docs/MAP.tsv` describing the tree before them, with a "Re-run docs_render.sh"
reminder. 8 of 50 such reminders ended the session unrendered, one executor
spent five tool calls deciding whether a render in the shared tree was its job,
and a render there would have left files that check 2 refuses the next merge on.
`crew done` now runs `docs_close --apply --refresh`, which refreshes whichever of
the two the repo keeps, and the close-out commit includes them. The flag is
opt-in because the caller must commit what it refreshes: a `scripts/crew`
stamped before 0.42.4 runs the bare `--apply`, commits only the Backlog doc and
`LOG.md`, and would be left an index that check 2 refuses on. The HTML pages stay out: they embed a stamp and
a git ref, so they would churn on every close-out; a full render refreshes them.
Second, the gates streamed the repo's own output: one green run put 10,539
characters of passing tests above the line that decided it, and executors had
begun piping `crew done` through `tail -40`, which also drops crew's own notes.
Stated ceiling: an executor branch that commits a rendered `INDEX.md` of its own
now meets a merge conflict on that generated file at step 1. None of the
ticket commits measured in four repos did so.

**Check 2 names a preview config, and the hat says how to preview a tree
(0.42.5).** The desktop app's Browser pane reads `.claude/launch.json` only from
the session's root, which for an executor is the main tree. Measured on
2026-09-26 over 46 executor sessions in four repos: 9 previewed a pool tree, and
none had a documented way to. Two added a `cd ../<repo>-e<k> && …` config to the
main tree's tracked `launch.json` and kept it there while their server ran; one of
those held a main tree dirty for over three hours, and another executor's
`crew done` waited behind it for 1h33 with the file listed and nothing more. Three
previewed the main tree's code instead of their own: a name that is not in the
main tree's `launch.json` does not fail, it starts another config from there
(reproduced the same day with a config in a second folder). Five `file://` opens
of a pool tree failed, including one whose file existed. So `worktrees.md` now
gives one path, a server started from the executor's own tree and opened by URL,
which never touches the main tree, and says that a named config, when needed, is
put back right after `preview_start`: a server already started from it keeps
running, and `preview_logs` and `preview_stop` keep working, tried the same day.
Check 2 still refuses on the file, because it counts every file; it now also
prints `[done:preview]`, what the file is and the command that puts it back. It
asks git about that one path rather than reading its own list, because a new
`.claude/` shows there as `?? .claude/`. Considered and dropped: exempting the
file from check 2. It would have unblocked 1 of the 11 real check-2 refusals in
those repos and none of the wrong-tree previews, it would be the first file check
2 does not count, and a ticket whose own merge touched the file would then fail
the fast-forward and be reported as "dev kept moving".

**A closer that skipped its branch is named, not refused (0.42.2).** Measured
twice on 2026-09-24 with a real executor session (Haiku): it ran `crew new 332`
and got e1 on `work/b332`, then committed the ticket's work, trailer and all,
straight onto main in the **main** tree, redid it in e1 and ran `crew done 332`.
Nothing noticed. Check 2 sees only uncommitted files, `log.tsv` got `SIZE
declared=1 actual=0`, and from the second the stray commit landed the board read
e1 as `finishing` while e1 had no commit at all. The signature is a commit
carrying the ticket's closer that is not on `work/b<nnn>`'s first-parent line. A
range such as `work/b<nnn>..<dev>` would find it only until `crew done` merges
the dev branch into the branch; a run that then dies on a red test leaves it
merged, and the rerun would read clean. On the first-parent line it stays a
second parent for good, so the board, the title and `crew done` read the same
answer before and after any merge. The board prints `bypass=<sha>` on the row
and stops counting that commit toward `finishing`. `crew done` still lands the
ticket, prints `[done:bypass]` with the sha, logs a `BYPASS` line, and the
carried summary (§1) repeats the flag so the final report does too. It warns and
never refuses, because the stray commit already sits on the shared dev branch and
a refusal would undo nothing while holding back the close-out. Stated ceiling: a
stray commit **without** the trailer looks like any other commit on the dev
branch, and nothing here can tell whose it was.

Executors merge their own finished work — no human review gate holds a green
branch. The gate that was removed was measured first: finished work waited
overnight, 7h18, and 6h55 *while every session was open*; nobody read the code
during the wait, so the gate bought nothing and widened every branch↔dev gap.

`crew done` also records declared-vs-actual size: if the Backlog item carries
optional `scope_files:` (the planner's S estimate), the actual
`git diff --stat` file count is logged next to it in `log.tsv`. The split
threshold (S > 6, complexity ≥ 3, or more-than-one-layer) rests on **one data
point** in the origin repo (median 2–3 files, max 10); this log is how the 6
stops being folklore.

### 6.1 `crew report` — the numbers are a command, the judgement is not

The same rule that made the merge a command (§6) applies to the weekly report,
from the other side: a report re-typed from memory keeps the story and loses the
numbers, and the numbers are the only part that can contradict the story.

`crew report [<period>] [--write]` measures the window and prints it. The window
runs from the **previous report's commit**, not from a calendar subtraction, so a
report written late still closes exactly where the last one ended — no commit is
counted twice and none falls between two reports. `--write` lays down
`92_audit/reports/<period>.md` with the measured section filled and every
judgement section empty; the command never writes prose about the project, and it
**refuses an existing file** (`[report:exists]`), because a report in `92_audit/`
is append-only and a correction is a new section at the end.

Cadence is derived, not configured: the board asks for a report only when the
window holds at least one landed ticket, and prints `report : none due` otherwise.
A config key for it would be a number to fill in wrongly (§9.3) in exchange for
nothing the activity does not already say.

## 7. Four gates before asking the user to decide

Gate 0 is STANDARD §5's lane test (three questions since 0.26.0 — the third
asks about irreversible side effects, and it outranks the other two: a 5-minute
rollback does not restore deleted data). "No" on all three → declare the fast
lane in the reply with a marker line and a reason. The marker is one line, at
line start:

```
LANE: fast — <reason>
```

| Gate | Obligation |
|---|---|
| 0 · lane | three questions; all-no → marker line, skip gate 2 |
| 1 · explain | BEFORE/AFTER diagram, two-sided trade-offs with numbers |
| 2 · confirm | ask **one to three check questions back**, one per core change, with AskUserQuestion, each only answerable from inside the model (level 2 — levels 0 "ok, got it" and 1 "repeat it back" catch only the reader's errors; the drawer's errors are the common ones) |
| 3 · ask | only now present the options |

Silence or a vague answer at gate 2 reads as *not understood* — stop; do not
present options. Since 0.42.3 there are one to three questions, one per core
change of the explanation (workflow or code), most important first, all in one
AskUserQuestion call. They guide rather than trap: the options are real
readings of the model plus a "not sure" option that names the section to
re-read, and an explanation file carries each answer folded under a click,
saying where a reader goes wrong and why. The owner asked for it after two
check questions typed at the end of the chat went unanswered in one session;
picking "not sure" reads as not understood, and gate 2 closes only when every
question is answered right. Record **which level** the confirmation reached, not just
"confirmed": a level-0 trace filed as "understood" makes the decision harder to
challenge later than no trace at all.

**The two-measurement rule** (gate 1, unenforceable, kept anyway): every number
that supports an irreversible action needs two independent measurements, and
one of the two must be capable of proving it wrong. Origin case: a count
returning `1` was pasted onto four diagrams as grounds for a permanent
deletion — the single record was a marker inserted by the startup probe, and
the true count was **0**. A 5-second query pointed the other way the whole
time. Right number, wrong reading, and four good-looking diagrams laundered it.

The gate-1 + gate-2 method is also packaged as a skill, `/docs-kit:explain
<topic>`. The model may invoke it on its own for one scope only — explaining
a layer-2 document or chain (Issue, Backlog, Proposal, Decision) — and every
other topic waits to be typed; `gates.md` in stamped repos keeps the law and
points there for the method.

## 8. Enforcement — three hooks, warn first, block by flag

Two PreToolUse hooks ship in 0.26.0 and one Stop hook in 0.37.0, all inheriting
STANDARD §8's doctrine
verbatim: deterministic, no LLM, **warn-only until tuned in practice**, silent
unless the repo opts in (a `.docs-kit.json` whose `crew` key exists).

1. **explain-gate** (on `AskUserQuestion`): reads the transcript **as events**,
   never as one string — it accepts a drawing-tool `tool_use` since the last
   human turn, a `SendUserFile` that shows a picture file (0.40.4), or the §7
   marker line inside an *assistant-authored text block*. The file counts when
   one path ends in `.html`, `.htm`, `.svg` or an image extension and
   `display` is anything but `"attach"`. It is matched on that payload and not
   through `draw_tools`, because crew-init writes that list into the config
   verbatim: 3 of the 4 crew repos measured carry it, so a new default entry
   would never reach them.
   Its own warning text never contains the literal marker: the origin repo's
   first gate matched strings over the whole transcript, and its refusal
   message contained both strings it was hunting, so it blocked exactly once
   and then held the door open forever. It reads the main transcript only, on
   purpose: a sub-agent's text never reaches the user as a reply, so its marker
   or drawing must not open the parent's question. The Stop scan does read
   `<session>/subagents/` (0.40.1), because an edit counts wherever it was made.
2. **resource-guard** (on `Bash`): when a command matches a declared resource's
   patterns and no session holds that lock → warn. Substring patterns; a
   wrapper script slips through unlogged. It measures the cooperative and
   misses the forgetful — that is its honest ceiling, same as a lock file
   someone creates by hand.

3. **title-nag** (on `Stop`, 0.37.0): the session title is the only place this
   model is visible from OUTSIDE a session. `crew status` derives every state
   from git, so the board stays right whatever the title says — the user's
   session list does not. An executor moves from `processing` to `finishing` the
   moment it writes the trailer and to `finished` when the close-out lands, and
   re-running `crew name` at either point (steps 4b and 5b of the hat) was
   reported as the most-skipped step, so sessions ended reading as work still in
   flight. The hook asks `crew name <role> --want` rather than deriving
   the grammar again: three parts read from git, one place, and this release adds
   the flag precisely so nothing else spells them out. Silent on a non-crew
   title, on a repo with no `scripts/crew`, and whenever `--want` refuses.

   Since 0.42.0 a title carries no `crew/` marker, so its second field is only a
   candidate role: it counts when `crew role` finds a stamped role file for it,
   which keeps a plain session titled `myapp · notes · …` out of reach. A title
   still in the pre-0.42 grammar is a crew title by its marker, and gets one nag
   that says so and carries it into the new grammar.

   **Known hole, stated rather than discovered:** `--want` is exactly what the
   `[name:place]` guard refuses for a `fast`/`full` ticket named from the main
   tree, so the hook goes quiet in the very case a nag would help most — a
   session that skipped `crew new` and is editing the shared tree. Fail open
   beats relaying a refusal the hook cannot act on, but it means this hook only
   ever helps sessions that were in the right tree to begin with.

Promotion to blocking is **per repo, per hook, by flag** — `"crew": {"enforce":
true}` turns explain-gate's warning into a deny; resource-guard stays warn-only
in 0.26.0. Three rules bind any future hardening, each learned from a hook that
failed:

1. **Read events, not strings.**
2. **Fail open, with a trail**: transcript unreadable → allow, plus one line in
   `gate.log`, so silence-from-broken never looks like silence-from-clean.
3. **Red on a known-bad case before it is trusted, red for the right reason**:
   the shipped test asserts the reason tag (`[gate:no-draw]`), not the exit
   code — a check that fails for a shape error also proves zero.

What the hook checks is *that a drawing happened*, never *that it was right*;
the two-measurement rule above has no enforcement and lives on discipline.
That is exactly where the origin repo got bitten once — stated here so it stays
a known hole, not a discovered one.

Nor does it check *that the reader saw it*. The tool result is the only thing
a transcript records, and in the case reported as docs-kit issue #3 the
visualize widget returned "rendered and shown" while the user saw no picture.
The gate opened correctly by its own rule. The `explain` skill carries the
remedy instead: the reader's word outranks the tool result, and the session
moves to the next surface.

## 9. Configuration — the `crew` key in `.docs-kit.json`

```json
{
  "owns": ["endpoints"],
  "crew": {
    "test_cmd": "npm test",
    "typecheck_cmd": "npx tsc --noEmit",
    "dev_branch": "main",
    "prod_branch": "production",
    "copy": ["node_modules", ".env", "harness"],
    "link": ["vendor-cache"],
    "setup_cmd": "",
    "roles_absent": [],
    "resources": { "e2e-harness": { "patterns": ["playwright", "docker compose"] } },
    "enforce": false
  }
}
```

**Absent `crew` key = the layer is off**: no hook fires, `crew` scripts refuse
politely, nothing scaffolded by an earlier version changes shape — the same
migration guarantee `owns` gives (STANDARD §9.1 rule 1). A minimal opt-in is
`"crew": {}`.

The block above holds sample answers, not defaults. What a reader uses when a
key is absent:

| Key | Asked by crew-init | Absent means |
|---|---|---|
| `test_cmd`, `typecheck_cmd`, `setup_cmd` | yes | `""`, the gate or step is skipped |
| `dev_branch` / `prod_branch` | yes | `main` / `production` |
| `copy` | yes | `["node_modules"]`; an empty list copies nothing |
| `link`, `roles_absent` | yes | `[]` |
| `resources` | yes | no locks |
| `enforce` | written as `false` | `false`, warn only |
| `reader_cap` | no, knob | `4` |
| `wait_budget_min` | no, knob | `30` |
| `draw_tools` | no, knob | `["mcp__visualize__show_widget", "Artifact"]` |
| `resetup_when` | no, knob | the seven usual lockfiles (§2) |

**Knobs stay absent until a measurement asks for one** (`setup.md` says which).
A present key outranks the default forever, so a knob written at its default is
a frozen copy that no later release can retune. Before 0.40.5, crew-init read
the block above as defaults and wrote them: 3 of the 4 crew repos measured
carried all three knobs in it at exactly the default, and none had tuned one.
`crew-update` step 5 finds such copies with `scripts/crew_knobs.py` and offers
to drop them. Dropping is a no-op on the day, because `crew_test.sh` holds the
script's table equal to every reader's fallback. `enforce` is written anyway:
STANDARD §8 fixes its default, so a written `false` cannot stand in the way of a
release, and `setup.md` tells people to flip it in place.

`draw_tools` names drawing tools only; a picture file sent to render opens the
explain-gate whatever the list says (§8).

`/docs-kit:crew-init` writes this key (asking, never guessing — the docs-init
asymmetry of §9.3), stamps `scripts/crew`, `.claude/crew/*.md` and
`.claude/commands/*.md` from `templates/crew/`, and offers the CLAUDE.md
snippet through AskUserQuestion with a text fallback, like every other write to
user config. Re-stamping after a kit upgrade belongs to `/docs-kit:crew-update`,
which is a separate skill for a reason measured in 0.26.3: crew-init's own guard
turns an already-on repo away, `docs-upgrade` only ever touched `docs/`, and the
two together left a repo stranded on the version it was stamped with. crew-update
re-stamps and nothing else — no interview, no config write — and it decides what
it may replace from the sha256 manifest at `.claude/crew/.stamp`, so a file the
scaffold wrote and nobody touched is updated in place while an edited one still
lands as `.new`.

**`dev_branch` is also what the tools outside crew should call the default.**
Claude Code's diff pane and the "Main branch … use this for PRs" line it loads
into every session read `refs/remotes/origin/HEAD`, and a clone points that ref at
the GitHub default, which in the commonest setup is `prod_branch`. Measured in the
repo that reported it: between two releases, every session diffed against prod and
saw 30 commits and 78 files that were not its own, and the PR hint named the one
branch that takes no direct commit. The fix is `git remote set-head origin <dev>`
in the main tree. It covers every worktree, because the ref lives in the git dir
they share, and it is local, so a fresh clone or `set-head -a` undoes it. So
crew-init offers it once `dev_branch` is written, crew-update offers it when the
board shows drift, and `crew status` prints a `default` row in the `main tree:`
block whenever the ref names another branch or is unset. The row is silent with
no `origin` remote, and it is left to the bottom note when `dev_branch` itself
does not exist, so one fault is reported once.

## 10. Deliberately absent from 0.26.0

| Absent | Why |
|---|---|
| Dashboard server | a fifth status surface (docs-check, three HTML views, `/now` exist); `crew status` is the data source, and a page can grow on top of it once someone actually misses one |
| `merge=union` gitattributes | audit lines are appended by `docs_close` on the main tree after the merge, serialized by construction; each ticket owns its own Backlog doc, so no two branches append to one ledger |
| `crew-check` skill | its two checks (orphan worktrees, ticket/tree drift) are deterministic, so they live inside `crew status`, not in a skill that would re-derive them |
| S/C fields in the validator | `scope_files:` and `execution:` stay optional and unchecked until the calibration log (§6) says what the thresholds should be |
| `brief` crew section | `brief` has its own measured gates; teaching its delegation prompt to name level, tree and branch deserves its own release |
| A report the machine writes | `crew report --write` fills the measured section and leaves every judgement section empty. Crew does not author prose about the project, for the reason §6.1 gives: the numbers are checkable and the story is not, so they must come from different hands |
| A board that fixes the branch | the main-tree line reports and never runs `git checkout`: whether sitting on another branch is deliberate is the one thing the board cannot know, and a status command that moves HEAD under a running session is not a status command |
| A board that sets `origin/HEAD`, or a key to silence its row | the `default` row names the fix and never runs it: repointing a ref every tool reads is the user's call, and someone who keeps it on prod on purpose pays one line on the board, which is cheaper than a config key that can be set wrong silently (§9) |
| Changing the GitHub default branch | it would also fix fresh clones and `gh pr create`, but it is a repo-wide setting that CI and every other clone read, so it belongs to the repo's owner; `setup.md` names it as the alternative |
| A monthly nag on the board | the four weekly lines already name the gap; only a state something acts on gets a word (0.32.0's rule) |
| Reports drawn on the HTML views | `docs_render.py` reads `92_audit/LOG.md` only, and the renderer is not touched this release; the audit line makes the report reachable from `changes.html` until someone draws it |
| A hook nagging an overdue report | hooks read events (§8) and a calendar is not one; the always-loaded snippet is at 2379 of its 2400-byte cap, so the reminder lives on the board that sessions are already told to run |
| A `roadmap_owner` / `report_every_days` key | one writer is a rule, not a setting, and the cadence is derived from landed work (§6.1) |
| Project groups made by the kit | measured once on the user's own sidebar: moving a session into a group flipped the whole sidebar out of its project view. A session joins a group only when the user already made it (§3) |
| A hook that files sessions into groups | hooks run in bash, and the sidebar is reachable only from the model inside the desktop app; the hook would need a tool it cannot call |
| A hook that blocks a stale title | title-nag warns and never denies: a title is a label on work already done, so blocking a session from ending over one would cost more than the wrong label does (§12) |
| Assigning a fork's other lanes | at a fork `crew done` continues into one successor and names the rest; who carries a second lane is the planner's call, like any other ticket, and a command that picked a session for it would be assigning work from a board |
| A chain field the validator checks for shape | `after_ref:` is a `*_ref`, so check 1 already resolves it; a loop or an Issue in it is caught where it bites — `crew new` refuses the Issue, `crew status` names the loop — and the validator stays on document shape (STANDARD §7) |
| `crew handoff <nnn>` generating the prompt | the template in the planner hat is filled by hand this release. A generator would make title and scope right by construction instead of by memory, which is strictly better and is exactly why it deserves its own release with its own measurement |
| A `PR` step in `crew done` | there is none to record: the merge is `--ff-only` onto the dev branch and the executor's report says so in as many words, because an empty PR field reads as "forgot to fill in" rather than "by design" |
| Node implementation | the origin repo's `lock.mjs` and hooks assumed Node on every machine; the port floor here is bash 3.2 + python 3.9 (STANDARD's own), so everything shipped is bash/py |

Open gaps carried from the origin repo, still open: executor-mix `p`
unmeasured (§5); split threshold on one data point (§6); no data yet on a
ticket spanning two technical layers — the model's central claim; template
command detection tuned on Node manifests.

## 11. Origin evidence

| Measured | Value | Rule it produced |
|---|---|---|
| One request through 4 roles | 15h32 total / ~87 min with commits | tickets cut by request, not layer (§1) |
| Finished work waiting for merge | 7h18 · 6h55 · overnight — 3× in 2 days | executor merges own work, no review gate (§6) |
| Ticket graded LIGHT holding the rig | 871 s | grader ≠ fixer (§3) |
| `p` on first two ops tickets | 0.78 · 0.36 | count lock slots, not tickets — and keep ops out of the executor formula (§5) |
| First two tickets under this model | 15 min · 41 min | one ticket – one branch – one executor (§1) |
| One manual pass playing the customer | 12 findings, suite green | tester explores, patches nothing (§3) |
| 93 commits in 2 days | 26 code · 46 docs · 21 rules | the execution layer deserves a standard (this file) |
| "A string match is not a measurement" | 5 bites in 1 day | procedures are commands (§6); hooks read events (§8) |
| Worktrees built vs sessions run in one | 4 trees · 49 s total · 0 sessions | the pool is persistent and the pin is the branch (§1) |
| Roadmap untouched while tickets closed | 10 days · 10 `Closes:` commits · 29 audit lines | the plan needs a writer of its own (§3) |
| `## Now` against the Backlog | 4 of 4 cited tickets done · 0 of 2 open cited | the board computes the drift, nobody remembers to look (§3) |
| Direction work cut as a code ticket | `BACKLOG-017`: 0 files, output gitignored, "do not close" | a survey is a report, not a ticket (§1, §3) |
| Report beside `LOG.md` vs in `reports/` | `status -> done` alone vs `status -> done, audit line` | the subfolder is what keeps close-out honest (§3) |
| One lock serialising two parallel trees | 30.7 h waited | an executor is not a second rig (§5) |
| 3 concurrent claims on a pool of 2 | 1 landed, 4 runs of 5 | claiming an executor is atomic (§4) |
| 2 concurrent acquires of one resource | both "succeeded", 5 of 5 | the write is the test, via O_EXCL (§4) |
| Diff pane between two releases, `origin/HEAD` on prod | 30 commits · 78 files, none the session's own | `origin/HEAD` follows `dev_branch`, offered and never forced (§9) |

## 12. When crew itself is wrong

Everything above tells an executor what to do. This section covers the case where
following it does not work: `crew done` merges in the wrong order, a lock is held
by a tree that no longer exists, a gate cannot be satisfied by any honest answer.

**Write it down in the repo that hit it, not in the reply.** One file per problem
in `docs/99_feedback/`, `about: crew`, created with:

```bash
bash "$PLUGIN_ROOT/scripts/docs_feedback.sh" new <slug>
```

The rule — which four cases qualify, which four do not, and why no field in it
ends in `_ref` — is STANDARD §12. Two things about it matter here specifically:

- **A workaround is the report.** §5's pacing and §6's merge procedure are both
  calibrated on a handful of measurements (§11), so the first thing that will be
  wrong about them is a threshold. The evidence that a threshold is wrong is
  somebody quietly working around it, and that evidence is worth more than an
  opinion about the number.
- **`severity: silent` outranks `blocks`.** A gate that refuses is visible and
  gets fixed. A hook that stays quiet when it should speak produces a session that
  looks exactly like a clean one — the same asymmetry §8 is built on, applied to
  the kit itself.

The reports stay in the repo after they are fixed. §10's list of what 0.26.0
deliberately left out was written from measurements taken in one repo over two
days; the next revision of it should be written from these.
