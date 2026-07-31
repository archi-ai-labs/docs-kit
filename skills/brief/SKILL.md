---
name: brief
description: Turn settled decisions into a delegation prompt for a coding agent, gating on a decision-freeze check first. In a repo that uses the docs-kit three-layer model it also records the work as an Issue and routes it through Layer 2 before the prompt is written. Use whenever the user is about to hand work to another agent or a teammate — a prompt, a spec, a work brief, a handover — and especially when they ask for one while key decisions are still open.
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

1. Print the open decisions as a short table first — decision · why it
   changes what gets built · your default — so the user sees the whole gate
   at once.
2. Then call AskUserQuestion, one question per open decision, **batched up
   to 4 per call**. A batch is one dialog to answer; a trickle of single
   questions is four chances to lose the user. More than 4 open decisions →
   ask the 4 that most change what gets built, then call again with the
   rest. For each question:
   - `header` ≤12 chars, naming the decision ("Storage", "Naming", "Retries")
   - 2–4 options, each a concrete buildable choice — never a bare Yes/No
     whose yes-branch still hides the real decision
   - your best-guess default FIRST, labelled `(Recommended)`, with the
     reason in its description
   - where delegation is genuinely fine, make that an explicit option
     ("Agent decides — any consistent choice works")
   - never author an "Other" option; the tool adds one
3. **In a `docs-kit` repo, add one more question to that same batch:** "record
   this work as an Issue?" — `header: "Record"`, options "Yes, record it now
   (Recommended)" and "No, just write the brief". It rides along in the dialog
   the gate was already going to show.

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

### Final pass — read it as the agent

Re-read the finished brief pretending you have zero conversation context:
- Where would you have to guess? → that's a missing decision or constraint
- Which instruction could be read two ways? → rewrite it
- Is any user-config-touching action (CLAUDE.md, settings) gated behind an
  ask-first rule? If not, add one.

Deliver the brief as a Markdown file the user can hand to the agent.

## After delivery — one-line lesson log

If the user reports the agent's result diverged from intent, do not just fix
the result. Diagnose: was the divergence caused by (a) a missing decision,
(b) a missing constraint, or (c) missing edge handling? Offer to append one
line to a `prompt-lessons.md` in the user's workspace. Patterns repeat —
after ~10 entries the user's 2-3 habitual gaps become visible and fixable.

## Anti-patterns to refuse

- Writing a polished prompt over unsettled decisions ("it looks complete" is
  not "it is decided") — run Phase 1 instead
- Running the Phase 1 gate in prose while AskUserQuestion is available — the
  questions scroll past, "go ahead" comes back, and nothing was decided
- Burying MUST/MUST-NOT rules inside descriptive paragraphs
- Omitting the WHY on deliberately unusual choices
- Prompts that give the agent no stop-and-ask escape hatch for edge cases
- Writing anything into `docs/` without the user having said yes to it
- Handing over full-lane work without surfacing that no Decision covers it —
  and equally, refusing to write the brief at all instead of asking
