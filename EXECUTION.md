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
| Session name | `<repo> · <e<k>\|main> · b<nnn> · <state> · crew/executor` | `myapp · e1 · b157 · processing · crew/executor` |

`<nnn>` is the zero-padded number exactly as it appears in `id:` — `crew`
normalizes `crew new 42` to `b042`.

Two addresses, and one thing joins them. The ticket number reaches the ticket,
its branch and its locks; the executor index reaches the tree and the session
that lives in it. What pins a ticket to an executor is **the branch that
executor has checked out**: git already stores it, git refuses to check one
branch out in two trees, and no file can disagree with it. `crew status` reads
that pin; nothing writes it. The session title is read off the same three
things — place, ticket, trailer — so it answers "where, which ticket, how far
along" without opening the board, and it cannot drift from what git says. The
place is `e<k>` for a pooled executor and **`main` for a fast-pair session**,
which skips the worktree and the branch but is still a session of its own. There
is deliberately **no idle title** and no ticketless one: an executor session
belongs to exactly one ticket, and without one there is nothing to name. An executor holding no ticket sits at a detached
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

**One ticket = one branch = one session, carried to `done`.** 0.31.0 changed
exactly one thing about that: the *tree* is no longer per ticket. A session is
still born for a ticket, titled `processing`, and ends `finished`; what is
reused is the checkout underneath it. The measurement that bought this rule:
one owner request ("fix the demo top-up") cut across 4 technical roles took
**15h32** wall-clock of which **~87 minutes** had commits, and the owner was
told "done" 4 separate times. The longest stretch was **7h18 of finished work sitting unmerged on a
branch** — which happened 3 times in 2 days. Cutting tickets by request instead
of by technical layer is the fix; the first two tickets run under this model
closed in **15 and 41 minutes**.

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

**A hat is only worn if the session list shows it.** §1 titles a ticket session
`<repo> · b157 · crew/executor`; a hat session drops the middle field and takes
`<repo> · crew/<role>`. The repo leads so any session list sorts by project, and
the ticket keeps the §1 token verbatim — `b157`, the same string the worktree
and the branch carry. `crew name <role> [<nnn>]` compares the running session
against that grammar and exits 1 when it does not match; `steward.md` runs it as
a hard first step, ahead of even read-only work.

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
applied to the main tree**, where a fast-pair session works: that tree is shared,
and `crew done` leaves writes there every run — `docs_close` flips the status and
appends the audit line without committing either. Reading dirtiness as "still
working" there would pin every fast-pair session at `processing` forever. The
main tree has its own guard instead, check 2 in §6.

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
   land, post-merge.
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
5. `git -C <main> merge --ff-only work/b157`, then push dev branch and work
   branch (skipped with a note when no remote exists). If the dev branch moved:
   back to step 1, at most twice.
6. Close-out: if a commit on the branch carries `Closes: BACKLOG-157`, run
   `docs_close` (STANDARD §6.1) so `status: done` and the audit line cite the
   sha; otherwise print the reminder and leave the flip to `docs-sync`. Release
   any locks still held by the ticket, then **park** the executor — detach it
   back onto the dev branch, which is what makes it free again. Its provisioned
   payload stays; any other uncommitted file keeps the executor on the branch
   and is named, exactly as the old teardown refused to delete it.

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
| 2 · confirm | ask **one check question back** that is only answerable from inside the model (level 2 — levels 0 "ok, got it" and 1 "repeat it back" catch only the reader's errors; the drawer's errors are the common ones) |
| 3 · ask | only now present the options |

Silence or a vague answer at gate 2 reads as *not understood* — stop; do not
present options. Record **which level** the confirmation reached, not just
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
   human turn, or the §7 marker line inside an *assistant-authored text block*.
   Its own warning text never contains the literal marker: the origin repo's
   first gate matched strings over the whole transcript, and its refusal
   message contained both strings it was hunting, so it blocked exactly once
   and then held the door open forever.
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
    "reader_cap": 4,
    "wait_budget_min": 30,
    "draw_tools": ["mcp__visualize__show_widget", "Artifact"],
    "enforce": false
  }
}
```

**Absent `crew` key = the layer is off**: no hook fires, `crew` scripts refuse
politely, nothing scaffolded by an earlier version changes shape — the same
migration guarantee `owns` gives (STANDARD §9.1 rule 1). Every field has the
default shown; a minimal opt-in is `"crew": {}`.

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
| A monthly nag on the board | the four weekly lines already name the gap; only a state something acts on gets a word (0.32.0's rule) |
| Reports drawn on the HTML views | `docs_render.py` reads `92_audit/LOG.md` only, and the renderer is not touched this release; the audit line makes the report reachable from `changes.html` until someone draws it |
| A hook nagging an overdue report | hooks read events (§8) and a calendar is not one; the always-loaded snippet is at 2379 of its 2400-byte cap, so the reminder lives on the board that sessions are already told to run |
| A `roadmap_owner` / `report_every_days` key | one writer is a rule, not a setting, and the cadence is derived from landed work (§6.1) |
| A hook that blocks a stale title | title-nag warns and never denies: a title is a label on work already done, so blocking a session from ending over one would cost more than the wrong label does (§12) |
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
