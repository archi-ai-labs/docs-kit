---
name: docs-upgrade
description: Bring an existing docs/ up to the current docs-kit standard — add folders and seed files this version ships that the repo lacks, regenerate the read models, and report what the deterministic checks now say. Adds only; never overwrites, edits, or deletes.
disable-model-invocation: true
---

# docs-upgrade — reconcile an existing `docs/` with the current standard

`docs-init` scaffolds a repo once. The standard then moves on: `04_api/` arrived in
0.20.0, `_archive/` and `INDEX.md` in 0.18.0, `99_feedback/` in 0.27.0, and a repo
scaffolded before those has no idea they exist. This skill closes that gap.

**Adds only.** It never overwrites a file, never edits one, never deletes one. An
existing file is the repo's content, and nothing here can tell an edited template
from a deliberate rewrite — so nothing here gets to guess. If a folder is missing it
appears with its seed file; if it is present, it is left exactly as it is.

If there is no `docs/` here, stop and suggest `/docs-kit:docs-init` — this skill
reconciles, it does not scaffold.

## Step 1 — Resolve the plugin root

In order: `$CLAUDE_PLUGIN_ROOT` → two levels above this SKILL.md →
`find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit` containing
`.claude-plugin/plugin.json`. Verify `$PLUGIN_ROOT/scripts/docs_scaffold.sh` exists.

## Step 2 — Sync the tree

```bash
bash "$PLUGIN_ROOT/scripts/docs_scaffold.sh" --sync .
```

It prints the repo's profile, one `added docs/…` line per item, and ends with
`SYNC OK`. Exit `3` means `docs/` does not exist — go back to the top. Relay the
added list verbatim; that is the whole answer to "what did this version bring".

**It syncs toward the profile, not toward all 17.** The first line of output says
which: `no owns declared` means this repo is held to the full tree exactly as it
always was, and `owns: data, endpoints` means it gets those folders and no others
(STANDARD §9.1). Nothing is ever removed — a folder the profile does not call for
but that already exists stays, with everything in it.

This is also the path when a repo **grows**. A backend that starts publishing an
API adds `endpoints` to `owns` in `.docs-kit.json`, runs this skill, and gets
`04_api/`. Changing `owns` is a layer 1 change, so the edit itself belongs to a
Decision — this skill does not make it, and will not offer to.

**Do not perform this copy by hand.** It used to be an instruction to an agent to
run `cp -Rn` carefully, which is a careful file operation living in a prompt. It is
a script now for that reason.

## Step 3 — Refresh the CLAUDE.md rules block

The block between `<!-- docs-kit:start -->` and `<!-- docs-kit:end -->` is the only
part of this kit loaded into **every** session of the repo, so a stale one costs more
than any other stale file here. It also drifts silently: `docs-init` writes it once
and nothing has ever updated it since, which is how repos ended up being told to run
`docs-sync` at the end of every session — a rule that predates the Stop hook knowing
which documents actually claim the edited files.

Compare the repo's block against `$PLUGIN_ROOT/templates/claude-md-snippet.md`. If
they already match, say so in one line and move on.

**Never write to CLAUDE.md without explicit consent — no exceptions.** Ask with
AskUserQuestion: "Refresh the docs-kit rules block in CLAUDE.md? It is N bytes today
and M in this version." Options: "Yes — replace the block" and "No — leave it".
If AskUserQuestion fails or comes back empty, ask in plain text and **end the turn**.

On yes, replace only the text between the two markers and change nothing else in the
file. No markers means the repo declined the block at init; do not add it here, and
say that `/docs-kit:docs-init` is where that choice belongs.

Show the user what changed in behaviour, not a diff of prose — which triggers were
dropped, which became conditional. That is the part they will feel.

## Step 4 — Regenerate the read models

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" .
```

Not optional. The sync may have added documents, and `docs/INDEX.md` is what `brief`
and `docs-sync` read **instead of** globbing folders — a stale index is worse than a
missing one, because the next agent trusts it. If the script exits 3 (`python3`
missing), say plainly that the read models were not regenerated and that skills must
fall back to reading folders until they are.

## Step 5 — Run the deterministic checks and report what changed

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
bash "$PLUGIN_ROOT/scripts/docs_render.sh" --check .
bash "$PLUGIN_ROOT/scripts/docs_render.sh" --check-api .
```

A newer standard checks more than the old one did, so a repo that was clean before
may now have findings. **That is the point, not a regression — say so.** Group them:

- **New folders and seeds** — from Step 2, with one line each on what the folder is
  for. `04_api/` in particular: an API contract is layer 1 now, which is what closes
  §6's old contradiction (it demanded a Decision for a thing it gave nowhere to record).
  `99_feedback/` is the other one worth a sentence: it is the first folder under
  `docs/` that is not about the product, and it is where a problem with the kit gets
  written down instead of said once in a session that then ends (STANDARD §12).
- **`NOTE [anchor]`** — paths a doc names that no longer exist. These were never
  checked before this version; they are pre-existing drift being surfaced, not damage
  the upgrade did. Say that plainly or it reads as breakage.
- **The other `NOTE` lines** — since 0.28.0 the validator fails on wrong *names* and
  only notes wrong *links* (STANDARD §7), so an upgraded repo may exit 0 while
  printing a dozen `NOTE [ref]` lines. Group them, do not bury them, and do not
  present them as failures: they are real findings the exit code deliberately
  ignores. `NOTE [stale]` and `NOTE [profile]` stay informational as before.
- **`FAIL [profile]`** — a token in `owns` that the standard does not define. It is
  a typo, and it costs the repo a folder: `"endpoint"` yields no `04_api/`. Say
  which token and what the valid five are; the fix is one character in
  `.docs-kit.json`, not a Decision.
- **Everything else** — normal validator findings.

## Step 6 — Offer the follow-ups, do not perform them

This skill changes no content. What it surfaces usually needs content work, and that
belongs elsewhere:

| Finding | Where it gets fixed |
|---|---|
| `NOTE [anchor]` on a moved path | `/docs-kit:docs-sync` (it is a layer 1 edit → Decision workflow) |
| Layer 1 docs with no `verified_at` | `/docs-kit:docs-sync`, once the code behind them has been read |
| Terminal Backlog/Issues still in the hot folders | `/docs-kit:docs-sync` Step 6 archives them |
| `NOTE [profile]` — `owns` no longer describes this repo | the user: `owns` in `.docs-kit.json` is a declared fact, and changing what a repo owns is a layer 1 change, so it goes through a Decision. Once it changes, run this skill again to get the folders it now justifies |
| An empty new folder | the user, when they have something to put in it. An empty `04_api/` is not a defect in a repo that declared `owns: endpoints` and has not written the contract down yet |

End with the validator's summary line and a one-sentence statement of what is now
different. Change nothing else on disk.
