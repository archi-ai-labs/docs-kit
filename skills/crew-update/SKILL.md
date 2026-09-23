---
name: crew-update
description: Re-stamp the crew layer of a repo that already has it — scripts/crew, the role commands, the operating docs — after docs-kit itself moved. No interview, no unasked config writes, safe to re-run. Use when the plugin was updated and this repo still carries the copies it was stamped with.
disable-model-invocation: true
---

# crew-update — carry a kit update into a repo that already runs crew

`crew-init` turns the layer ON, once. Nothing turned it FORWARD: its own guard
sends an already-on repo to `/docs-kit:docs-upgrade`, and that skill only
reconciles `docs/`. So a repo could sit on the version it was stamped with while
the kit ran three releases ahead, and the only way out was hand-copying files
out of the plugin cache. This skill is that missing half.

**It stamps what the kit owns and nothing else.** It never re-asks the
interview and never turns a role on or off. Besides the `.new` merges it may
ask two questions: step 4's about `origin/HEAD`, only when the board shows that
ref on another branch, and step 5's about frozen knobs, only when the config
carries one. The second is the only way this skill writes `.docs-kit.json`,
and only on "yes".

## Step 0 — Resolve the kit, and say which version is about to land

Plugin root, in order: `$CLAUDE_PLUGIN_ROOT` → two levels above this SKILL.md →
`find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit` containing
`.claude-plugin/plugin.json`. Then print the version:

```bash
python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" \
  "$PLUGIN_ROOT/.claude-plugin/plugin.json"
```

Say that number out loud before touching anything. A session runs the plugin
that was installed when it started, so if the number is older than the release
the user is after, stamping it would quietly install the old files again. In
that case stop and hand them these two lines, then ask them to restart the app
and call this skill again:

```
claude plugin update docs-kit@archi-ai-labs
claude plugin update docs-kit@archi-ai-labs --scope local
```

The second line only matters on a machine that also installed the plugin at
`local` scope; it is harmless otherwise, and skipping it on a machine that has
one is what makes an update look like it did nothing.

## Step 1 — Guards

1. Inside a git repository? If not, stop — crew is built on worktrees.
2. `.docs-kit.json` has a `crew` key, or `scripts/crew` exists? If neither, this
   repo was never turned on: send them to `/docs-kit:crew-init` and stop.

## Step 2 — Read the absent roles, then stamp

`roles_absent` records the roles the interview found this repo does not have.
The scaffold does not read config, so pass the list yourself — forget it and
this skill re-creates the exact ghost files `crew-init` refused to write.

```bash
SKIP="$(python3 -c "import json;print(','.join((json.load(open('.docs-kit.json')).get('crew') or {}).get('roles_absent') or []))" 2>/dev/null)"
bash "$PLUGIN_ROOT/scripts/crew_scaffold.sh" ${SKIP:+--skip "$SKIP"} .
```

Relay the output verbatim. Its last line counts four classes, and each means a
different thing:

| Line | What happened |
|---|---|
| `stamped:` | the file was missing and now exists |
| `updated:` | the kit's own copy, untouched since it was written, replaced in place |
| identical | already current, nothing done |
| `review :` | the file differs AND is not what the kit last wrote — a human edited it |

`updated:` is the one that makes this skill worth typing: it is decided by the
sha256 manifest at `.claude/crew/.stamp`, not by a guess. A repo stamped before
that manifest existed has none, so its first run reports `review :` for
everything that moved — that is expected once, and the manifest that run writes
makes every later update automatic.

## Step 3 — Finish the `review :` files, with the diff in front of the user

For each `<file>.new`, show what actually changed — `diff -u <file> <file>.new`,
trimmed to the interesting hunks — and say in one sentence what the kit added.
Then ask which ones to apply (AskUserQuestion; a plain list works as fallback).
Apply only the ones chosen:

```bash
mv "<file>.new" "<file>"
```

Never apply them all silently. A `review :` file is by definition one somebody
edited on purpose, and in `.claude/crew/` that somebody is usually the steward
writing a rule the repo learned the hard way — the exact content that must not
vanish under a kit update.

## Step 4 — Prove it runs, then report

```bash
scripts/crew help
scripts/crew status
```

If the board's `main tree:` block has a `default` row, `origin/HEAD` names a
branch other than `dev_branch`, and every repo stamped before 0.40.3 was set up
without anything checking it. Ask the question from crew-init's step 3.5, with
the same facts in it, and run `git remote set-head origin <dev>` only on "yes".
When the row says to push first, say so and do not push. This is a git ref,
not `.docs-kit.json`.

## Step 5 — Frozen knobs: offer to drop them, never unasked

```bash
python3 "$PLUGIN_ROOT/scripts/crew_knobs.py" .
```

`KNOBS none` or `KNOBS off` → say nothing and move on. Each `[knob:frozen]`
line is a tuning knob this config carries at exactly the kit's current default,
which is what crew-init wrote before 0.40.5. Ask one question (AskUserQuestion,
text fallback) that names each key with its value and states three facts:

- dropping changes nothing today, because each value equals the default the
  readers fall back to (crew_test checks that table against the readers);
- once dropped, a later release that retunes a default reaches this repo; kept,
  the repo stays on today's value for good;
- a value kept on purpose means answering "no" on every run, or setting a
  different value, which the script never reports.

On "yes", run the same script with `--drop` and relay its lines. Then say that
`.docs-kit.json` changed and needs a commit; do not commit it yourself.

```bash
python3 "$PLUGIN_ROOT/scripts/crew_knobs.py" --drop .
```

Then report four things: the version now stamped, the counts from step 2, any
`.new` left unapplied by the user's own choice, and the knobs dropped or kept. If `scripts/crew` was among
the updated files, mention that open executor sessions are still running the old
copy in their worktrees — the file follows the branch, not the session.

**Coming from before 0.34.0**, say this: the repo gains a sixth hat. Because this
skill never interviews, `navigator.md` simply lands as `stamped:` and the hat is
on — the next `crew status` grows a `direction:` block that will very likely name
a stale `## Now` column and a missing weekly report. That is drift which was
already there, not something the update caused. A repo that does not want the hat
adds `"navigator"` to `crew.roles_absent` in `.docs-kit.json` by hand and re-runs;
the scaffold then reports `skipped:` and the block goes quiet. Mention too that a
ticket shaped like direction work — no code files, deliverables in a gitignored
folder, "do not close this" written in the body — is the navigator's report now,
and the planner's to close as Layer-2 bookkeeping.

**Coming from before 0.31.0**, say this and stop there: the repo has no executor
pool yet, so `crew new` will refuse until someone runs `scripts/crew executor
add`; any surviving `../<repo>-b<nnn>` tree still merges by hand and `crew
status` names it. Do not create the pool or remove a tree yourself — pool size
is the planner's call and a `-b` tree may hold unmerged work.
