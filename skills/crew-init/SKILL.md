---
name: crew-init
description: Turn on the crew execution layer in this repo — interview for commands/branches/resources, write the `crew` key into .docs-kit.json, stamp scripts/crew + role commands + operating docs, and offer the CLAUDE.md snippet. One-time per repo; everything after runs without this skill.
disable-model-invocation: true
---

# crew-init — one-time setup of the execution layer

You configure; the scripts do the stamping. **Ask, never guess** (the §9.3
asymmetry): a wrong value in `.docs-kit.json` silently changes how merges and
hooks behave.

## Step 0 — Guards

Resolve the plugin root (in order: `$CLAUDE_PLUGIN_ROOT` env var → two levels
above this SKILL.md → `find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit`
containing `.claude-plugin/plugin.json`). Then check, in order:

1. Inside a git repository? If not: stop — crew is built on worktrees.
2. `docs/23_backlog/` exists? If not: suggest `/docs-kit:docs-init` first and
   stop — crew rides the Backlog (EXECUTION §1), there is no second ticket
   system to fall back to.
3. `.docs-kit.json` already has a `crew` key? Then this repo is already on;
   say so and point re-stamping to `/docs-kit:crew-update` instead. Stop.
   (It used to point at `docs-upgrade`, which only ever touched `docs/` — so an
   already-on repo had no route forward at all and sat on the version it was
   stamped with.)

## Step 1 — Detect, as proposals only

Gather evidence and show it with the source attached (like `owns-hint:`):

- **the two branches, which get their own step below** — collect the evidence
  here and decide nothing: every local branch with its last commit date and
  whether it tracks a remote (`git for-each-ref --sort=-committerdate
  refs/heads --format='%(refname:short) %(committerdate:short) %(upstream:short)'`),
  which one the main tree has checked out now, and `origin/HEAD` if it is set;
- test / typecheck commands: `package.json` scripts, `Makefile` targets,
  `pyproject.toml` — quote the line you read them from;
- dependency dirs that exist: `node_modules`, `vendor`, `.venv`;
- executor payload: the gitignored things a fresh checkout will lack — nested
  repos (`find . -maxdepth 3 -name .git -not -path ./.git`), env files
  (`.env*`), dep dirs — proposed as `copy` (mutable), `link` (strictly
  read-only shares), and a `setup_cmd` for whatever needs a command.

## Step 1.5 — The two branches: ask, and say what each one costs

These two answers are not settings, they are where work lands. Get either wrong
and the repo keeps running while doing the wrong thing, which is why they are
asked on their own rather than buried in a list of four.

**Say what the branch is FOR, in the question itself.** A user picking from bare
branch names is guessing; a user who knows what will happen to the branch is
choosing:

| Answer | What it means for the rest of the repo |
|---|---|
| `dev_branch` | every executor cuts `work/b<nnn>` **from** it, and `crew done` merges **back into** it `--ff-only`. The main tree must have it checked out or `crew done` refuses at check 1. This is the branch the whole pool moves. |
| `prod_branch` | devops holds it and the `/release` procedure is the only thing that advances it, `--ff-only` from dev, so its history stays a prefix of dev's. It takes no direct commit and no executor ever touches it. This is the branch a deployment is cut from. |

**Offer the real branches as the options, each with its evidence** — last commit
date and upstream from step 1 — and mark the one the main tree currently holds.
Rank the suggestion, do not invent it:

- for `dev_branch`: the checked-out branch first, then the most recently
  committed branch. Say which rule produced the suggestion.
- for `prod_branch`: a branch named `production`, `prod`, `release` or `main`,
  preferring one that tracks a remote, then `origin/HEAD`'s target — each only
  **when it is not already the dev answer**.

`origin/HEAD` is evidence about the GitHub default, not about where work lands.
In the commonest setup that default is the prod branch, which is why it ranks
for prod and no longer for dev: as a dev suggestion it pointed the whole pool at
the branch that takes no direct commit. Step 3.5 then reconciles the ref with
whatever the user answered.

**A repo with one branch is a real answer, not a failure.** Then dev and prod
are the same branch, `/release` is a tag rather than a merge, and that is worth
saying out loud so nobody later reads the equal values as a mistyped config.
Recording no prod branch at all is also allowed and lands in step 1.6's
`roles_absent` as `devops` + `release`.

**Never write a branch that does not exist.** If the user names one that is not
in `git branch`, either create it in front of them (`git branch <name> <dev>`,
asked first) or record the answer and warn that `crew status` will keep printing
`prod_branch '<name>' does not exist` until someone does. A config naming a
ghost branch is the §9.3 error class again.

## Step 1.6 — Role readiness: warn, then ask; never stamp a ghost

Every system tests and deploys differently, and a stamped command file for a
role this repo does not actually have is a wrong fact in the repo — the same
error class §9.3 exists to prevent. Evidence per role:

| Role | Evidence it exists here |
|---|---|
| tester | a real test command from step 1, or an e2e resource worth a lock |
| devops + release | step 1.5 produced a prod branch that is different from the dev branch, or the repo carries deploy artifacts (a Dockerfile, a deploy workflow) |

A role with NO evidence **must be raised with the user — warn first, then ask;
this is a hard requirement, not a courtesy.** Three honest answers: it exists
(collect the missing command or branch), it does not yet (record it in
`roles_absent`, skip its command file), or the user defers (same as not-yet,
said out loud). `planner`, `executor`, `steward` and `navigator` need no check
— a repo with a Backlog, a git tree and a `00_roadmap/` (core in every profile)
has them by construction. The reason `tester` and `devops` need evidence is that
their duties rest on infrastructure outside the docs model; the navigator's only
tools are git and `docs/`. **A roadmap still identical to the seed is not missing
evidence — it is the navigator's first job**, the same way an empty executor pool
is `crew new`'s, so gating the hat on it would withhold it from exactly the repo
that needs it most.

## Step 2 — Interview (AskUserQuestion, text fallback)

Ask, in up to two rounds of four, offering the detected values as defaults:

1. test command + typecheck command (empty = skip that gate in `crew done`);
2. the two branches from step 1.5 — ask this one on its own, with the
   consequence of each answer stated, never as two bare names in a list;
3. executor provisioning — which detected payload goes in `copy`, which in
   `link` (read-only only — never link something a ticket edits), and the
   `setup_cmd` if any;
4. shared resources, as `name: pattern, pattern` lines (empty is fine — locks
   can be declared later in `.docs-kit.json`);
5. the step 1.6 question, one per role that lacked evidence;
6. consent to append the crew snippet to `CLAUDE.md` (**writes to user config
   only via this question** — on "no" or no answer, print the snippet path
   `templates/crew/claude-md-crew-snippet.md` for manual pasting and move on).

`enforce` is not a question: it starts `false`, and `setup.md` documents the
evidence needed before anyone turns it on.

## Step 3 — Write the config

Merge the `crew` key into `.docs-kit.json` **without touching other keys**
(read-modify-write via python3 json, not sed). If the file does not exist,
create it containing only `{"crew": {...}}` — an absent `owns` stays absent,
so the docs profile behaves exactly as before (STANDARD §9.1 rule 1).

Write the fields the interview asked about — `test_cmd`, `typecheck_cmd`,
`dev_branch`, `prod_branch`, `copy`, `link`, `setup_cmd`, `resources`,
`roles_absent` — even when an answer equals the fallback, plus `enforce: false`.
An answer is a fact about this repo: `dev_branch: "main"` must not move when a
later kit changes its fallback.

**Never write a tuning knob** — `reader_cap`, `wait_budget_min`, `draw_tools`,
`resetup_when`. A present key outranks the kit's default forever, so a knob
written at its default is a frozen copy: 3 of 4 crew repos measured carried all
three written knobs at exactly the default, none tuned, and 0.40.4 could not
change `draw_tools`' default for them. `setup.md` says when a measurement earns
a knob its line; EXECUTION §9 lists every fallback.

## Step 3.5 — `origin/HEAD`: offer to point it at the dev branch, never unasked

The dev answer says where the pool works, but the tools outside crew take their
base branch from `refs/remotes/origin/HEAD`, and a clone points that ref at the
GitHub default — in the commonest setup, the prod branch. Claude Code's diff pane
then shows every unreleased commit instead of the session's own work (30 commits
and 78 files in the repo that reported it), and the "Main branch … use this for
PRs" line it loads into every session names the branch that takes no direct
commit. When the ref is unset, Claude Code guesses `origin/main`, then
`origin/master`.

```bash
git config --get remote.origin.url        # no origin → skip this step silently
git symbolic-ref -q refs/remotes/origin/HEAD
git show-ref --verify refs/remotes/origin/<dev>
```

Skip silently when there is no `origin`, or the ref already reads
`refs/remotes/origin/<dev>`. Otherwise ask one question (AskUserQuestion, text
fallback), and put these facts in it rather than after it:

- the command is `git remote set-head origin <dev>`, run in the main tree. The ref
  lives in the git dir every worktree shares, so one run covers the whole pool;
- it is local to this machine. A fresh clone or `git remote set-head origin -a`
  points it back at the GitHub default, and `crew status` then shows a `default`
  row until someone runs the command again;
- it does not change the GitHub default branch, so `gh pr create` without `--base`
  still targets that. Changing the GitHub setting is a decision for the repo's
  owner, since CI and every other clone read it too; this skill never touches it.

Run the command only on "yes". If `origin/<dev>` does not exist, `set-head`
refuses it, so say that the dev branch must be pushed first and do not push it
yourself. On "no", move on: the board row is the reminder, and it names the fix.

## Step 4 — Stamp

```bash
bash "$PLUGIN_ROOT/scripts/crew_scaffold.sh" --skip <roles_absent, comma-joined> .
```

(omit `--skip` when `roles_absent` is empty). Relay its
`stamped:`/`review:`/`skipped:` lines verbatim. It adds and never clobbers; a
`.new` file means a local edit survived and needs a human merge.

## Step 5 — Snippet (only if consented in step 2)

Append the content of `templates/crew/claude-md-crew-snippet.md` to the repo's
`CLAUDE.md` (create the file if absent). If the `docs-kit:crew:start` marker is
already present, replace the block between the markers instead of appending a
second copy.

## Step 6 — Hand over

Report in a few lines: what was written where, then the working loop — the
planner pre-warms the pool if it wants to (`scripts/crew executor add`, twice by
default) and writes the first ticket, `scripts/crew new <nnn>` hands it to a free
executor and creates one if none is free,
`scripts/crew done <nnn>` lands it and frees that executor — or, for a session
opened with `crew new <nnn> --chain` and a ticket another one names in
`after_ref:`, hands it straight to that one — `scripts/crew
status` before taking more. Then the weekly loop, which is the navigator's:
`scripts/crew report --write` measures the window and lays down
`docs/92_audit/reports/<week>.md` with its judgement sections empty, and the same
hat then syncs the roadmap's `## Now` column. Point to `.claude/crew/README.md`
as the 30-second map, and name what is missing out loud: absent roles and a prod
branch that does not exist yet stay visible in `crew status` until someone wires
them, and so do a `## Now` column that has stopped matching the Backlog and an
`origin/HEAD` the user chose to leave on another branch. Do not run
`crew executor add` or `crew new` yourself; the first ticket is the user's call,
and an empty pool is not a problem — the first `crew new` builds what it needs.
