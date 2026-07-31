---
name: brief
description: Turn settled decisions into a delegation prompt for a coding agent, gating on a decision-freeze check first. Use whenever the user is about to hand work to another agent or a teammate — a prompt, a spec, a work brief, a handover — and especially when they ask for one while key decisions are still open.
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

Work in two phases. **Never skip Phase 1.**

## Phase 1 — Decision freeze check (gate)

Before writing anything, scan the conversation (or the user's description)
and list:

1. **Settled decisions** — things explicitly chosen, with reasons if given
2. **Open decisions** — anything where you or the user would have to guess:
   - structure/architecture choices not yet made
   - naming, ordering, or conventions still fuzzy
   - edge cases with no defined behavior
   - conflicts with things the user built before (check memory/context)

**Gate rule:** if open decisions exist that materially affect what gets
built, STOP. Do not write the prompt. Present the open decisions as a short
table and resolve them with the user first (one question at a time, offer
your best-guess default for each). Only proceed to Phase 2 when the list of
open decisions is empty or explicitly delegated ("agent may decide X
freely").

Tell-tale sign the freeze is incomplete: while drafting, you catch yourself
inventing an answer ("hmm, which way should this go?"). That invented answer
is an unsettled decision leaking into the prompt — go back and settle it.

### If the repo uses the three-layer docs model

When the target repo has a `docs/` tree scaffolded by docs-kit, the freeze
check gets a shortcut and a rule:

- Settled decisions may already be recorded in `docs/22_decisions/` — cite
  their ids (`DECISION-NNN`) in the brief instead of re-explaining them, and
  check `docs/02_architecture/` for constraints the brief must not violate.
- A decision that was only made in chat but would change
  `docs/02_architecture/` is full-lane work: it belongs in the
  Issue → Proposal → Decision flow before any brief is written. Offer to
  record it properly (e.g. via `/docs-kit:docs-sync`) instead of freezing it
  informally inside the prompt.

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
- Burying MUST/MUST-NOT rules inside descriptive paragraphs
- Omitting the WHY on deliberately unusual choices
- Prompts that give the agent no stop-and-ask escape hatch for edge cases
