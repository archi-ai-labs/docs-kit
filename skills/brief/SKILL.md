---
name: brief
description: Turn settled decisions into a delegation prompt for a coding agent, gating on a decision-freeze check first. In a repo that uses the docs-kit three-layer model it also records the work as an Issue and routes it through Layer 2 before the prompt is written. Use whenever the user is about to hand work to another agent or a teammate — a prompt, a spec, a work brief, a handover — and especially when they ask for one while key decisions are still open.
# Both fields are load-bearing, and they fix two DIFFERENT surfaces — never drop
# one as redundant. In the terminal CLI, picking a command from the / menu submits
# it immediately unless the skill declares `arguments` with at least one name; only
# then does the menu leave `/docs-kit:brief ` sitting in the input, waiting. In the
# desktop app nothing suppresses the run — instead the app injects an elicitation
# instruction built from `argument-hint`, so with the hint the turn opens by asking
# for the subject and without it the model has to guess one from this file.
# The quotes around the hint are required: bare [brackets] parse as a YAML list.
argument-hint: "[what the work is about]"
arguments: subject
---

# Brief — from settled decisions to a delegation prompt

You are helping the user write a delegation prompt (work brief) for a coding
agent, based on the current conversation and/or the description they provide
with this command. If they passed arguments, treat them as the subject:
$ARGUMENTS

A good delegation prompt is not good writing — it is a **record of decisions
that were already settled**. Most bad prompts fail because they were written
too early, while key decisions were still open. The agent then builds exactly
what was described, including the parts that were never thought through.

Work in phases. **Never skip Phase 1.** Phase 0 and Phase 1.5 run only in a repo
that uses the docs-kit three-layer model; everywhere else this is the same
two-phase skill it has always been, and it writes no file but the brief.

## Phase 0 — Detect the repo

One check, no guessing:

```bash
test -d docs/20_issues && echo docs-kit || echo plain
```

- **`plain`** — this repo does not use the three-layer model. Run Phase 1 and
  Phase 2 exactly as written, skip Phase 1.5, and ignore every mention of
  Issues below.
- **`docs-kit`** — Phase 1 gains one question, Phase 1.5 runs, and Phase 2
  cites ids instead of restating decisions.

**Why the detection is one directory test and not a heuristic:** this skill has
to stay usable in any repo. Something that guesses ("this tree looks
documented") would start writing Issues into projects that never opted in.
`docs/20_issues/` exists only because someone ran docs-init.

## Phase 1 — Decision freeze check (gate)

### In a `docs-kit` repo, read what is already settled first

Some decisions are already on disk, and asking the user to re-make them is how
a gate wastes its one dialog. Before anything else, read `docs/22_decisions/` —
a decision recorded there is settled, and the brief cites its id
(`DECISION-NNN`) rather than re-explaining it. Read `docs/02_architecture/` too,
for constraints the brief must not violate.

A decision that was only ever made in chat is **not** settled just because the
user sounded certain about it. That one goes through the gate, and then through
Phase 1.5, like everything else.

### The gate itself

Before writing anything, scan the conversation (or the user's description)
and list:

1. **Settled decisions** — things explicitly chosen, with reasons if given
2. **Open decisions** — anything where you or the user would have to guess:
   - structure/architecture choices not yet made
   - naming, ordering, or conventions still fuzzy
   - edge cases with no defined behavior
   - conflicts with things the user built before (check memory/context)

**Gate rule:** if open decisions exist that materially affect what gets
built, STOP. Do not write the prompt — not a draft, not an outline, not "a
first pass to react to".

**Resolve the gate with AskUserQuestion. Always — this is not optional.** A
gate asked in prose scrolls off the terminal and gets answered with "ok, go
ahead"; that is exactly how an unsettled decision ends up frozen into the
brief. The tool renders a dialog the user has to answer — that is the whole
reason it is mandatory here.

**This survives the desktop app's elicitation instruction, which says the
opposite.** When this skill is invoked with no arguments, the Claude Code
desktop app injects a block starting `[Skill "brief" was invoked. It expects:
…]` that forbids AskUserQuestion and routes to the `visualize` elicitation
widget instead. That instruction governs **argument collection** — finding out
what the work is about, before Phase 1 has anything to scan. The gate is a
different act: it resolves decisions the conversation left open, mid-task,
after that subject is already known. Collect the subject however the host
asks; resolve the gate with AskUserQuestion regardless. **Do not "reconcile"
the two by moving the gate onto the elicitation widget** — the widget is a
desktop-only tool, and a gate that silently does nothing in the terminal CLI
is worse than no gate at all.

1. Print the open decisions as a short table first — decision · why it
   changes what gets built · your default — so the user sees the whole gate
   at once.
2. Then call AskUserQuestion, one question per open decision, **batched up
   to 4 per call — 4 is the tool's hard ceiling, not a house style**. A batch
   is one dialog to answer; a trickle of single questions is four chances to
   lose the user. More open decisions than fit in a call → ask the ones that
   most change what gets built, then call again with the rest. For each
   question:
   - `header` ≤12 chars, naming the decision ("Storage", "Naming", "Retries")
   - 2–4 options, each a concrete buildable choice — never a bare Yes/No
     whose yes-branch still hides the real decision
   - your best-guess default FIRST, labelled `(Recommended)`, with the
     reason in its description
   - where delegation is genuinely fine, make that an explicit option
     ("Agent decides — any consistent choice works")
   - never author an "Other" option; the tool adds one
3. **In a `docs-kit` repo, one of those four slots is already spoken for.**
   Add this question to the same batch: "record this work as an Issue?" —
   `header: "Record"`, options "Yes, record it now (Recommended)" and "No,
   just write the brief". It rides along in the dialog the gate was already
   going to show, which leaves **at most 3 open decisions in that first
   call**; any beyond that go to the follow-up call step 2 already provides
   for.

   **Why the slot is reserved rather than borrowed:** a fifth question is not
   dropped — it makes the whole call invalid, and an AskUserQuestion that
   fails lands in step 4, which asks in prose and ends the turn. So the one
   arrangement that must never happen is the gate with the *most* to settle
   being the one that degrades into the prose gate this skill spends five
   paragraphs forbidding.

   **Why it is folded into the gate's batch instead of asked on its own:** the
   Issue has to be written while the decisions are still open — that is what
   `status: exploring` is for — and nothing may be written into `docs/` without
   the user's say-so. Asked separately it lands as a second dialog immediately
   after four real questions, and a second dialog in a row is the one people
   dismiss without reading. One dialog satisfies both rules.

   When the gate finds **no** open decisions there is no batch to ride along
   in: ask this one question by itself.
4. If AskUserQuestion is unavailable, fails, or returns an empty answer: ask
   the same questions in plain text, numbered, and **end the turn**. Never
   proceed on silence.
5. A general "go ahead" / "ok làm đi" is not an answer to a specific
   decision — re-ask the ones still open.

Only proceed to Phase 2 when every open decision is answered or explicitly
delegated ("agent may decide X freely").

Tell-tale sign the freeze is incomplete: while drafting, you catch yourself
inventing an answer ("hmm, which way should this go?"). That invented answer
is an unsettled decision leaking into the prompt — go back and settle it.

### Closing the gate in a `docs-kit` repo

If the user said yes in step 3, write the Issue **now**, while the open-decision
table is still in front of you. Mechanics live in
`references/issue-capture.md` at the plugin root (resolve the root as in
docs-init Step 0). The Issue opens at `status: exploring` and its body carries
that table — unless the gate found nothing open, in which case there was never
anything to explore and it opens at `status: open`.

**An Issue left behind by an abandoned gate is not litter.** If the user walks
away mid-gate it stays at `exploring`, which is precisely what STANDARD §4 says
that status is for: "raw research, not yet a real Issue". Do not archive it, do
not delete it, do not write cleanup logic for it.

## Phase 1.5 — Route the Issue through Layer 2

`docs-kit` repos only, and only when an Issue was recorded in Phase 1.

The gate has closed: every open decision now has an answer. Promote the Issue to
`open` if it is still `exploring` — it will already be `open` when the gate found
nothing to ask about — then run the lane test: STANDARD §5, two questions, any
"yes" means FULL. Full mechanics, including how the Backlog item is written
and why the forward path appends no audit line, are in
`references/issue-capture.md`.

| Lane | What happens |
|---|---|
| FAST | Create the Backlog item (`source_ref` = the Issue), flip the Issue to `promoted`, continue to Phase 2. |
| FULL | Leave the Issue at `open`. **Stop and ask** — see below. |

### Full lane — ask, never decide

Full lane means the work touches Architecture or is expensive to reverse, and
no Decision exists for it yet. That is exactly the situation the three-layer
model was built to catch. It is **not** a reason to refuse: call
AskUserQuestion with two real options —

- **Stop here, draft the Proposal** — no brief is written this turn. Produce the
  Issue and offer to start `docs/21_proposals/`, whose body needs a genuine
  "Alternatives considered" section (STANDARD §4).
- **Hand the work over anyway** — write the brief, and stamp a block into its
  HARD CONSTRAINTS section saying no Decision covers this work and Architecture
  must not be amended without one.

**Why this asks instead of blocking:** docs-kit's hooks are warn-only on
purpose (STANDARD §8) — a false positive that blocks teaches people to rip the
whole plugin out, which costs every bit of enforcement it had. The same
reasoning governs this skill. Never refuse to write the brief; make the missing
Decision impossible to miss instead.

If AskUserQuestion is unavailable, ask the same two options in plain text and
**end the turn**.

## Phase 2 — Write the brief

Use this 6-section skeleton. Sections may be renamed but none may be
silently dropped:

```
1. CONTEXT         who the user is, the situation, how this connects
                   to things that already exist (other repos, plugins,
                   conventions the user follows)
2. SOURCE OF TRUTH the core model/spec, marked "do not alter" —
                   diagrams and tables, not prose
3. CONCRETE ASKS   each deliverable, with expected structure AND
                   expected behavior
4. HARD CONSTRAINTS what is FORBIDDEN and what is MANDATORY —
                   kept separate from descriptive text so the agent
                   cannot mistake rules for suggestions
5. EDGE HANDLING   "if you encounter X, stop and ask the user —
                   do not decide yourself"
6. EXPECTED OUTPUT what the end state looks like and how to verify it
```

Section 5 inherits the gate rule: every "stop and ask the user" the brief
writes must say **ask with AskUserQuestion, and end the turn if the tool is
unavailable** — otherwise the receiving agent asks in prose and the user
misses it there too.

In a `docs-kit` repo, section 2 **cites rather than restates**: name the
`BACKLOG-NNN` this work came from, the `ISSUE-NNN` behind it, and any
`DECISION-NNN` that constrains it. The docs are the source of truth; a brief
that paraphrases them creates a second copy that will be wrong within a month.
Restate only what the receiving agent cannot look up.

### Three techniques that make the difference

**a. Explicit delegation rights.** Every brief must answer three questions:
- What may the agent NOT change? (the frozen model)
- What may the agent decide freely? (implementation details)
- What must the agent stop and ask about? (edge cases, user config files,
  merges)

Agents fail mostly because they don't know how far their authority extends.

**b. Record the WHY at fragile points.** Anywhere a future reader (agent or
human) might "optimize" a deliberate choice into something else — write the
reason inline. Example: a warn-only hook must carry a comment explaining why
it is not block-mode yet, or someone will "fix" it and break the design.

**c. Tables for relationships, prose for reasoning.** Folder mappings, field
lists, trigger→action pairs → tables. Design philosophy and trade-off
explanations → short prose. Never invert this.

### Section 6 always states what makes it fail — a writing rule, not a question

`how to verify it` was too weak on its own. Every brief's section 6 must name **what makes
the result fail**, and must **fail closed**: a criterion nobody could confirm is a failure,
never a pass. Where the repo has a real check, name the actual command rather than "the
tests".

**This costs no dialog and applies to every brief, split or not.** Acceptance criteria are a
property of the work; *who* runs the check is a property of how the work is staffed, and
that is settled only when the work is split (below). Do not promote this into a question —
a brief whose criteria you had to ask for is a brief drafted too early.

### When the deliverables can be split — the parallelisation block

Some briefs describe work several agents could do at once. **Deciding how it splits is
itself a decision**, which is why it is settled here and not in Phase 1: the partition
cannot be named before CONCRETE ASKS exists, so a question asked earlier could only take
the bare Yes/No shape the gate rule forbids — and nothing in Phases 1 or 1.5 depends on
the answer.

Spell it **"Claude Code's Workflow tool"** in full every time — in this repo "workflow"
already means the Decision workflow, and a bare mention will be read that way.

#### Step 1 — is the work even big enough to ask about? Measure, do not eyeball

Count, from the drafted CONCRETE ASKS:

- **D** — deliverables that do not depend on each other
- **P** — distinct files or directories they write between them

**When `D < 3` or `P ≤ 2`, do not ask at all.** Run serially and say nothing about it.

**Why there is a floor:** fan-out is not free. It costs a dialog, a partition someone has
to check, N agents that each re-read the whole brief, a merge you supervise, and a
verification pass. Under a small brief that overhead exceeds the wait it saves — and a
dialog offered on a two-file change is exactly how a user learns to dismiss this dialog on
the change where it mattered. The floor is a measurement, not modesty; do not lower it
because a task *feels* big.

**When you do ask, the counts go in the option labels** — "Split by deliverable (4 asks,
11 files)", never "Split by deliverable". An option built from real numbers is one the
user can answer; a placeholder is one they guess at.

#### Step 2 — the disjointness test, four checks, all must pass

1. **Lane FULL → never split.** Full lane means the work touches Architecture or takes more
   than a day to reverse. Both are statements about shared state.
2. **Any ask that writes a shared file → serial.** Shared means `docs/**`, `CHANGELOG.md`,
   the plugin version file, `.gitignore`, generated HTML, the audit log, the roadmap: one
   namespace or one anchor, and no merge story.
3. **Write one line per ask — `agent-N → the exact paths it may write`.** A path in two
   rows, or a row you cannot enumerate, → serial. If the table cannot be written, the work
   is not decomposed enough to split.
4. **Read-only asks are always safe.** Analysis, tracing, review — no collision surface.

#### Step 3 — ask whether to split

AskUserQuestion, `header: "Split"`, options that are concrete partitions carrying the
counts from step 1, never a bare Yes/No. Recommend **serial** by default; recommend it
especially when the lane was FULL and the brief carries the no-Decision stamp, since
fanning that work out multiplies the blast radius of exactly what the stamp warns about.

**This gate's fallback is the opposite of every other gate in this skill, and that is
deliberate.** Elsewhere an unavailable AskUserQuestion means ask in prose and end the turn,
because silence would freeze an unsettled decision. Here the brief already exists in draft
and silence means serial — the status quo, and a harmless one. So: ask in prose, and if no
answer comes, **deliver the brief serially anyway**. Ending the turn here would strand a
finished brief, which is the one outcome the delivery rule below calls a non-delivery.

#### Step 4 — after a parallel answer, one dialog settles the rest

Only after the user picked a parallel option. Everything here exists **because** the work is
being split — a single agent has nobody to collide with and needs none of it. One
AskUserQuestion call, four questions, exactly at the cap.

**These are proposals, not requests for input.** You have just drafted the whole brief and
run the disjointness test, so you already know the paths and the counts. Never ask the user
to *list* anything: put your derived answer up as the first option, labelled
`(Recommended)`, with the real numbers in the label and the actual detail in the
description. **AskUserQuestion adds its own free-text entry to every question — that entry
is how the user adds to or overrides your proposal**, which is precisely why this file
forbids authoring an "Other" option yourself. Whatever comes back, free text included, is
written into the brief verbatim.

- `header: "Scope"` — section 3's write ownership. *"As drafted — 4 asks, 11 files
  (Recommended)"*, with the per-agent path list in the description; then a narrower
  alternative that names the riskiest subset and says what it defers.
- `header: "Verify"` — section 6's *checker* (its fail criteria are already written by the
  rule above). *"An agent that did not build it re-reads the files (Recommended)"* / *"You
  review the diff before anything lands"* / *"the repo's own check must pass"* — naming the
  real command, never a placeholder.
- `header: "Mode"` — **"Inspect first, then decide" (Recommended)** / "Write straight away".
  The first runs the fan-out read-only: every agent reports what it *would* change and
  writes nothing. This is the one parameter a brief could never express before, and it is
  the cheapest way to find a bad partition — a wrong split costs a report instead of a
  merge.
- `header: "Ceiling"` — how many agents may run at once. Offer real numbers derived from
  **D**, and state that anything above the ceiling is left for a later run.

If AskUserQuestion is unavailable here, **fall back to serial and deliver the brief** —
never run a fan-out on assumed parameters.

#### Step 5 — what must be true before anything runs

1. **The brief is written and delivered first**, at its real path. The fan-out reads it
   from there. Never hand agents a brief that exists only in this conversation.
2. **Every document id the work needs is pre-allocated by you, here, and written into the
   brief as a literal.** No agent may run the allocator. Id allocation is read-then-write
   with no lock, and per-agent views of `docs/` make a collision certain rather than
   likely — and `references/issue-capture.md` forbids renumbering, so nobody can repair it.
3. **No agent gets an isolated worktree.** `briefs/` is gitignored with no tracked files,
   so a worktree starts without it and silently destroys the brief — the very defect the
   delivery rule below exists to prevent. Disjointness is what makes isolation unnecessary,
   and step 2 already proved it.

#### Step 6 — run it as a dynamic workflow

Call Claude Code's Workflow tool with a script you compose **from this brief**, inline. This
skill ships no orchestration script of its own, on purpose: the partition differs for every
brief, and a fixed script would only be a worse version of what the brief already says. The
brief *is* the input — sections 3, 4 and 6 carry scope, split strategy, shared files, the
ceiling and the check, which is precisely what a workflow script needs to be written from.

The composed script must do these four things, and the user can watch it run with
`/workflows`:

1. **Re-check the partition in code before spawning anything** — refuse on paths that
   overlap between two deliverables, on any path under a shared file, and on a deliverable
   whose paths could not be enumerated. **This duplication is deliberate:** a prompt saying
   "do not collide" is a request, while a partition rejected before any agent starts is a
   fact. Step 2 already established the facts; the script enforces them.
2. **`pipeline()` the deliverables, one agent each**, passing each agent its own exhaustive
   path list, the shared-file list it may never write, and — in inspect-first mode — the
   instruction to report what it *would* change and write nothing.
3. **Verify each finished deliverable with a second agent** that reads the files rather than
   the builder's report, defaults to fail when it cannot confirm, and also reports any file
   written outside the paths that agent owned.
4. **Return structured results**: what each deliverable did, every blocker, every needed
   change to a shared file, whatever the ceiling dropped, and whatever failed verification.

`isolation: 'worktree'` appears nowhere in it — step 5 says why.

#### Step 7 — when it returns, the caller finishes the job

- **Surface every blocker before merging anything.** A fanned-out agent cannot ask, so it
  records the blocker and stops that deliverable. Put those in front of the user with
  AskUserQuestion.
- **Apply `sharedFileNeeds` yourself, serially.** Agents describe changes to shared files;
  they never make them.
- **Report what the run did not do** — deliverables the ceiling dropped, rows the guards
  rejected, deliverables that failed verification, and any file written outside its
  ownership. Never let a cap read as full coverage.
- In a `docs-kit` repo, run the validator and the renderer **exactly once, after everything
  has landed** — never inside an agent.

#### The five things a split brief must carry — and where each lives

The skeleton stays at six sections. Every piece has a home already:

| What a split brief needs | Where it goes | Why it is needed |
|---|---|---|
| **Scope** — the `agent-N → deliverable → exact writable paths` table, and whether the pass is read-only | 3 CONCRETE ASKS | Bounding *authority* was never enough; two agents need bounded *paths*. Read-only mode makes an inspect-first pass expressible at all. |
| **Split strategy** — the partition itself and the boundary it follows | 3 CONCRETE ASKS | The partition is the decision this whole block exists to freeze. |
| **Shared files + ceiling** — files no agent may own, and how many agents may run | 4 HARD CONSTRAINTS | A ceiling is **mandatory**: without one nothing the brief says bounds how far the work fans out. |
| **Verification** — how each deliverable is checked *by someone who did not build it*, and what makes it fail | 6 EXPECTED OUTPUT | A lone agent checking its own output is the weakest check in the brief; once work is split there is finally someone else to do it. The verifier reads files, not reports, and fails closed. |
| **Blocked-agent rule** — record the blocker and stop, do not decide | 5 EDGE HANDLING | The escape hatch had to change shape; see below. |

**Section 5's escape hatch changes shape here, and only here.** The rule above says every
stop-and-ask must name AskUserQuestion — that assumes a receiving agent with an interactive
turn. A fanned-out agent has no such tool, so "end the turn" inside one means it returns
quietly while the others keep writing. In a split brief section 5 therefore reads *record
the blocker in your result and stop work on that deliverable*, and the brief must say the
blockers get surfaced before anything is merged. Do not "simplify" this back to the
AskUserQuestion phrasing: it would put an instruction in the brief that the receiving agent
cannot obey.

Technique **a** also gains a fourth question in a split brief: *what may this agent not
touch because another agent owns it?* That is distinct from the frozen model — the frozen
model is shared by everyone, an ownership boundary belongs to one agent.

### Final pass — read it as the agent

Re-read the finished brief pretending you have zero conversation context:
- Where would you have to guess? → that's a missing decision or constraint
- Which instruction could be read two ways? → rewrite it
- Is any user-config-touching action (CLAUDE.md, settings) gated behind an
  ask-first rule? If not, add one.

### Delivering it — where the file goes, and what happens to it after

Write the brief to **`<repo-root>/briefs/`**, creating that directory if it is
not there. Name it `brief-<slug>.md`, lowercase ASCII with hyphens — the same
rule STANDARD §11 puts on document file names, for the same reason. When a brief
is one of an ordered series, a two-digit prefix is fine: `brief-03-<slug>.md`.

**Print the full absolute path when you hand it over.** A brief the user cannot
find is a brief that was not delivered.

| Rule | Why it is this way |
|---|---|
| `briefs/` belongs in that repo's `.gitignore` | A brief is the reasoning that led to a change, and `CHANGELOG.md` is where that reasoning belongs once the change lands. Commit both and the repo holds two copies of the same decisions — and the brief, frozen at hand-over, is the copy that goes stale. |
| Adding that line is a write to a file the user owns, so **ask first** | AskUserQuestion; if it is unavailable, ask in plain text and end the turn. Never edit a `.gitignore` silently. If the repo has none at all, that is a bigger act than appending — stop and ask before creating one. |
| **Nothing ever deletes a brief** — not this skill, not a hook, not `docs-sync` | The brief holds decisions that were already settled: it is the record of *why* shipped code looks the way it does. Deleting it on a timer, or on "the work is done", throws that away for a few kilobytes. The user deletes briefs when the user decides to. This is the same rule Phase 1 states for an abandoned Issue — do not add cleanup logic here later either. |

**A session scratchpad is not a home.** A brief written to a temp directory is
filed under an opaque session id, outside git and outside backup, and is never
found again — which is exactly how seven of them silently accumulated before
this rule existed.

## After delivery — one-line lesson log

If the user reports the agent's result diverged from intent, do not just fix
the result. Diagnose: was the divergence caused by (a) a missing decision,
(b) a missing constraint, or (c) missing edge handling? Offer to append one
line to `<repo-root>/briefs/prompt-lessons.md` — the same gitignored directory
the brief itself went to, so one rule covers everything this skill writes.
Patterns repeat — after ~10 entries the user's 2-3 habitual gaps become
visible and fixable.

## Anti-patterns to refuse

- Writing a polished prompt over unsettled decisions ("it looks complete" is
  not "it is decided") — run Phase 1 instead
- Running the Phase 1 gate in prose while AskUserQuestion is available — the
  questions scroll past, "go ahead" comes back, and nothing was decided
- Leaving the brief somewhere the user was never told about — a scratchpad, a
  temp path, or a `briefs/` whose location you did not print
- Burying MUST/MUST-NOT rules inside descriptive paragraphs
- Splitting deliverables whose writable paths overlap — two agents editing one
  file is a merge conflict the brief itself caused
- Asking whether to split before CONCRETE ASKS is drafted: with no deliverables
  to partition, the only askable question is the bare Yes/No the gate forbids
- Offering the split dialog on work below the size floor — the overhead exceeds
  the wait it saves, and it trains the user to dismiss the dialog that mattered
- Asking the user to *list* write paths or acceptance criteria instead of putting
  up a draft they can correct — you wrote the brief, so you already know both,
  and a question you could have answered yourself is homework handed back
- Making a serial brief pay for coordination machinery: path ownership and an
  independent checker exist because two agents can collide, and one cannot
- Fanning out before the brief is delivered to its real path, or before every id
  it needs is pre-allocated as a literal
- Giving a fanned-out agent an isolated worktree — `briefs/` is gitignored, so
  the worktree starts without it and destroys the brief
- Reporting a capped run as if it covered everything — always name what the
  ceiling dropped, what the guards rejected, and what failed verification
- Omitting the WHY on deliberately unusual choices
- Prompts that give the agent no stop-and-ask escape hatch for edge cases
- Writing anything into `docs/` without the user having said yes to it
- Handing over full-lane work without surfacing that no Decision covers it —
  and equally, refusing to write the brief at all instead of asking
