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

- dev branch: current branch of the main tree, or `origin/HEAD` if set;
- prod branch: a branch named `production`/`prod`/`release` if one exists;
- test / typecheck commands: `package.json` scripts, `Makefile` targets,
  `pyproject.toml` — quote the line you read them from;
- dependency dirs that exist: `node_modules`, `vendor`, `.venv`;
- executor payload: the gitignored things a fresh checkout will lack — nested
  repos (`find . -maxdepth 3 -name .git -not -path ./.git`), env files
  (`.env*`), dep dirs — proposed as `copy` (mutable), `link` (strictly
  read-only shares), and a `setup_cmd` for whatever needs a command.

## Step 1.5 — Role readiness: warn, then ask; never stamp a ghost

Every system tests and deploys differently, and a stamped command file for a
role this repo does not actually have is a wrong fact in the repo — the same
error class §9.3 exists to prevent. Evidence per role:

| Role | Evidence it exists here |
|---|---|
| tester | a real test command from step 1, or an e2e resource worth a lock |
| devops + release | the prod branch exists in `git branch`, or deploy artifacts (a Dockerfile, a deploy workflow) |

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
2. dev branch + prod branch;
3. executor provisioning — which detected payload goes in `copy`, which in
   `link` (read-only only — never link something a ticket edits), and the
   `setup_cmd` if any;
4. shared resources, as `name: pattern, pattern` lines (empty is fine — locks
   can be declared later in `.docs-kit.json`);
5. the step 1.5 question, one per role that lacked evidence;
6. consent to append the crew snippet to `CLAUDE.md` (**writes to user config
   only via this question** — on "no" or no answer, print the snippet path
   `templates/crew/claude-md-crew-snippet.md` for manual pasting and move on).

`enforce` is not a question: it starts `false`, and `setup.md` documents the
evidence needed before anyone turns it on.

## Step 3 — Write the config

Merge the `crew` key into `.docs-kit.json` **without touching other keys**
(read-modify-write via python3 json, not sed). If the file does not exist,
create it containing only `{"crew": {...}}` — an absent `owns` stays absent,
so the docs profile behaves exactly as before (STANDARD §9.1 rule 1). Fields
and defaults: EXECUTION §9 — including `copy`/`link`/`setup_cmd` from step 2
and `roles_absent` from step 1.5.

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
`scripts/crew done <nnn>` lands it and frees that executor, `scripts/crew
status` before taking more. Then the weekly loop, which is the navigator's:
`scripts/crew report --write` measures the window and lays down
`docs/92_audit/reports/<week>.md` with its judgement sections empty, and the same
hat then syncs the roadmap's `## Now` column. Point to `.claude/crew/README.md`
as the 30-second map, and name what is missing out loud: absent roles and a prod
branch that does not exist yet stay visible in `crew status` until someone wires
them, and so does a `## Now` column that has stopped matching the Backlog. Do not run
`crew executor add` or `crew new` yourself; the first ticket is the user's call,
and an empty pool is not a problem — the first `crew new` builds what it needs.
