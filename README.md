# docs-kit

[![validate](https://github.com/archi-ai-labs/docs-kit/actions/workflows/validate.yml/badge.svg)](https://github.com/archi-ai-labs/docs-kit/actions/workflows/validate.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-8A63D2.svg)](https://docs.claude.com/en/docs/claude-code)

> A **Claude Code plugin** that keeps a repo's docs true to its code: three
> layers, one direction of change, deterministic checks, and an HTML view built
> from the markdown. An optional crew layer runs the tickets in parallel.

Architecture docs drift from the code until nobody can say which decision caused
which change. `docs-kit` fixes the direction of change instead of asking for
discipline: **only a Decision amends Architecture**, every change traces back to
an Issue, and what a machine can check, a script checks.

**Requirements:** Claude Code **v2.1.154+** (older versions install the plugin
switched on) and **Python 3.9+** for the renderer and the hooks. Without Python
the hooks stay silent and the renderer skips with a message. Always-on context
cost: **about 400 tokens**.

**Menu:** [Install](#-install) · [Usage](#-usage) · [The model](#-the-model) · [Crew](#-crew) · [Generated views](#-generated-views) · [Enforcement](#-enforcement) · [Upgrade](#-upgrade-a-repo) · [Uninstall](#-uninstall) · [For maintainers](#-for-maintainers) · [Roadmap](#-roadmap)

---

## 🚀 Install

Two ways to install. **Option 1 is recommended.**

### Option 1 — One command in your terminal ⭐

```bash
curl -fsSL https://archi-ai-labs.github.io/agent-marketplace/install.sh | bash -s -- --plugins docs-kit
```

This installs for every project (`~/.claude/settings.json`); add `--project` to
write `./.claude/settings.json` for the current folder only. It is safe to re-run:
it backs up `settings.json` first and aborts if the JSON is invalid.

### Option 2 — Inside Claude Code (Windows / no bash)

```
/plugin marketplace add archi-ai-labs/agent-marketplace
/plugin install docs-kit@archi-ai-labs
```

`/plugin install` **does not default to global** — it asks for a scope:

- **User** — every project → **pick this for global**
- **Project** — this repo, shared (`.claude/settings.json`)
- **Local** — this repo, just you (`.claude/settings.local.json`)

> The shell form `claude plugin install docs-kit@archi-ai-labs` installs to
> **User** scope with no picker.

### ▶︎ After installing

1. Restart Claude Code (or `/reload-plugins`), and trust the `archi-ai-labs`
   marketplace if asked.
2. **Option 2 only:** `/plugin enable docs-kit@archi-ai-labs`, because that route
   installs the plugin switched off.
3. Run **`/docs-kit:docs-init`** in the repo you want documented.

<details>
<summary><b>Extras</b> — why Option 2 lands off · read the script first · local dev · what the installer writes</summary>

### Why Option 2 lands off

`docs-kit` registers five hooks, which run without you asking at that moment, so
the plugin ships `defaultEnabled: false`. Option 1 makes you name
`--plugins docs-kit` — without it the installer enables only `trim-kit` — and that
is the decision: the installer writes an explicit `true` into `enabledPlugins`,
which outranks the default. A choice already in your settings outranks it too.

### Prefer to read the script before running it?

```bash
curl -fsSL https://archi-ai-labs.github.io/agent-marketplace/install.sh -o install.sh
less install.sh   # review
bash install.sh --plugins docs-kit   # then run
```

### Local dev — try it without installing

```bash
claude --plugin-dir /path/to/docs-kit   # session-only, writes no settings
```

### What the installer actually writes

The script deep-merges these two keys into the target `settings.json`; you can
add them by hand instead:

```json
{
  "extraKnownMarketplaces": {
    "archi-ai-labs": {
      "source": { "source": "github", "repo": "archi-ai-labs/agent-marketplace" }
    }
  },
  "enabledPlugins": {
    "docs-kit@archi-ai-labs": true
  }
}
```

</details>

---

## 💡 Usage

Every command is typed as `/docs-kit:<name>`.

| Command | What it does | Writes files |
|---|---|---|
| `docs-init` | Start here: scaffold `docs/`, fill Architecture from the code | Yes |
| `docs-sync` | End of session: statuses, audit lines, drift | Yes |
| `docs-check` | Validate, and explain each failure; never fixes | No |
| `docs-render` | Rebuild the HTML views, `INDEX.md` and `MAP.tsv` | Generated only |
| `docs-upgrade` | Bring `docs/` up to this version | Adds only |
| `docs-archive` | Move finished chains into `_archive/` | On your yes |
| `brief` | Turn settled decisions into a prompt for another agent | On your yes |
| `explain` | Explain an Issue, a Decision or a mechanism, with a drawing | No |
| `crew-init` | Turn on [crew](#-crew) for this repo | On your yes |
| `crew-status` | Read-only board: executors, tickets, locks | No |
| `crew-update` | Carry a new kit version into a crew repo | Kit files |

**Typical flow:** `docs-init` once → work → `docs-sync` at the end of a session →
`docs-check` whenever you want the structure verified.

```text
$ /docs-kit:docs-init
  → scaffolds docs/, reads the source, renders the HTML views
$ /docs-kit:docs-sync
  → flips backlog statuses, appends audit lines, flags undocumented drift
```

---

## 🧭 The model

```
LAYER 1  FOUNDATION  Products → Roadmap → Architecture → API
LAYER 2  CHANGE      Issue → [Proposal → Decision] → Backlog
LAYER 3  REFERENCE   Conventions, services, runbooks, deploy, QA
OVERSIGHT            audit log (append-only) · kit feedback
```

Layer 1 changes only through a Decision, and Layer 3 is edited directly. A change
that modifies Architecture, takes over a day to revert, or has an irreversible
side effect goes through a Proposal and a Decision; anything else goes straight
from Issue to Backlog. The full model is in [STANDARD.md](STANDARD.md), and its
known limits are in [DESIGN-NOTES.md](DESIGN-NOTES.md).

---

## 👥 Crew

Optional, and off until `/docs-kit:crew-init`. Crew runs approved Backlog items in
parallel: a planner cuts tickets, each executor works one ticket on its own branch
in its own git worktree, and `scripts/crew done` tests, merges and closes it.
Shared resources are locks, so two executors never hold the same one. The process
is in [EXECUTION.md](EXECUTION.md).

---

## 🖼 Generated views

`docs-render` writes three HTML pages for people, `INDEX.md` for agents and
`MAP.tsv` for the hooks: same input, same bytes, no LLM. Agents trust `INDEX.md`,
so gate it in CI with `docs_render.sh --check .`. See a
[real sample](design/sample-current.html).

---

## 🔒 Enforcement

Five deterministic, warn-only hooks, silent in a repo that has not opted in. Two
watch the docs: an edit to Architecture, and code that moved past the document
describing it. Three watch crew: a shared resource used without its lock, a
question asked before any drawing, and a session title that git no longer agrees
with. They warn rather than block, because a hook that blocks on a false positive
gets switched off ([STANDARD §8](STANDARD.md), [EXECUTION §8](EXECUTION.md)).

---

## 🔄 Upgrade a repo

Updating the plugin does not update your repos. While every executor is `idle`:

1. `claude plugin update docs-kit@archi-ai-labs` in a terminal, then restart.
2. `/docs-kit:docs-upgrade`
3. `/docs-kit:crew-update`, in crew repos only.
4. Commit, then `/docs-kit:docs-check`.

<details>
<summary><b>Details</b> — local scope, <code>.new</code> files, one-off steps by version</summary>

**Local scope.** A repo that pins the plugin at local scope needs step 1 again
with `--scope local`, run inside that repo. `crew-update` names the version about
to land on its first line; if it is not the new one, step 1 has not taken effect.

**A `.new` file** means someone edited that file after the kit wrote it. Taking
the `.new` drops the edit; keeping yours drops the kit's change. When both
matter, apply what `github.com/archi-ai-labs/docs-kit/compare/v<old>...v<new>`
shows for that file to your copy, and delete the `.new`.

**One-off actions, by the version you come from:**

| Coming from before | Also do |
|---|---|
| 0.44.0 | Remove `briefs/` from every executor tree (`../<repo>-e<k>/briefs`), after `diff -rq ../<repo>-e<k>/briefs briefs`: a report an executor wrote there exists nowhere else |
| 0.42.0 | Nothing. Each open crew session is told once to move to the new title grammar |
| 0.34.0 | The `navigator` hat arrives on. To opt out, add `"navigator"` to `crew.roles_absent` in `.docs-kit.json` and run step 3 again |
| 0.31.0 | `crew new` refuses until the planner runs `scripts/crew executor add` |

The **Upgrading** paragraphs of [CHANGELOG.md](CHANGELOG.md) are the source of
this table.

</details>

---

## 🧹 Uninstall

```
/plugin uninstall docs-kit@archi-ai-labs     # remove the plugin
/plugin disable docs-kit@archi-ai-labs       # or only turn it off
/plugin marketplace remove archi-ai-labs     # drops the catalog AND every plugin from it
```

Run `/reload-plugins` to apply. A script install can also be undone by deleting
`extraKnownMarketplaces["archi-ai-labs"]` and `enabledPlugins["docs-kit@archi-ai-labs"]`
from `settings.json`, or by restoring the `.bak` the installer left beside it.
Your `docs/` is plain markdown and keeps working without the plugin.

---

## 🛠 For maintainers

<details>
<summary><b>Validate before sharing</b></summary>

```bash
claude plugin validate .    # manifest + skill frontmatter
```

That and the full test recipe run on every push and PR via
[`.github/workflows/validate.yml`](.github/workflows/validate.yml): manifest and
script syntax on the Python 3.9 floor, a fresh scaffold for every profile, the
validator, both `--check` gates, every hook, the crew end-to-end suite, and
`design/sample-*.html` against a fresh render. Most steps are **mutation tests**
— they break something on purpose and assert the check fails. A gate that has
only ever been seen passing is not a gate.

</details>

<details>
<summary><b>Test recipe</b> — what to run by hand</summary>

```bash
# scaffold into a scratch repo and validate it
work="$(mktemp -d)"; git -C "$work" init -q
bash scripts/docs_scaffold.sh "$work"
bash scripts/docs_validate.sh "$work/docs"     # arg is the DOCS dir, not the repo root
bash scripts/docs_validate.sh --strict "$work/docs"   # CI mode: link findings fail too

# render, reproducibly
DOCS_KIT_NOW=2026-07-31T09:30:00 python3 scripts/docs_render.py "$work"

# the two read-only gates — write nothing, exit 1 on drift
bash scripts/docs_render.sh --check "$work"        # is INDEX.md current?
bash scripts/docs_render.sh --check-api "$work"    # does 04_api match the generated artifact?

# scaffold a profile instead of the full tree — 13 folders here, not 17
lib="$(mktemp -d)"; bash scripts/docs_scaffold.sh --owns data,endpoints "$lib"

# file a problem with the kit itself — the created file IS the prompt to send
bash scripts/docs_feedback.sh new hook-stayed-quiet "$work"
bash scripts/docs_feedback.sh list "$work"
bash scripts/docs_feedback.sh show FEEDBACK-001 "$work"

# regenerate the design samples — must produce no diff
bash design/make-samples.sh && git diff --stat -- design/
```

Mutating an enum, an audit line or a duplicated `id:` must turn the validator's
`OK` into `FAIL` lines. Mutating a ref, an `amended_by` entry or a path named in
`components` must produce `NOTE` lines, which become `FAIL` under `--strict`: a
wrong name fails, a wrong link warns (STANDARD §7).

</details>

<details>
<summary><b>Cut a release</b></summary>

The version lives in exactly one place — `.claude-plugin/plugin.json` — so it
never drifts. The renderer reads it and stamps it into every generated page.

1. Bump `version` in `.claude-plugin/plugin.json`.
2. Regenerate the samples: `bash design/make-samples.sh` (they carry the version).
3. Move the `Unreleased` notes into a dated section in [CHANGELOG.md](CHANGELOG.md).
4. Commit, then tag: `git tag v<x.y.z> && git push --tags`.

> CI enforces this: pushing a tag `v<x.y.z>` fails the build unless it matches
> `version` in `plugin.json`, so steps 1 and 4 cannot silently drift apart.

Installs do not follow `main` on their own; each user picks the new version up
with step 1 of [Upgrade a repo](#-upgrade-a-repo).

</details>

<details>
<summary><b>Project layout</b> — a standalone plugin, not a marketplace</summary>

This repo is a **standalone plugin**, distributed through the `archi-ai-labs`
marketplace whose catalog lives in the separate
[`archi-ai-labs/agent-marketplace`](https://github.com/archi-ai-labs/agent-marketplace)
repo — so there is no `marketplace.json` here, only a `plugin.json`.

```
docs-kit/
├── .claude-plugin/plugin.json   # the plugin manifest (single source of version)
├── .github/workflows/validate.yml
├── STANDARD.md                  # source of truth for the docs model
├── EXECUTION.md                 # source of truth for the crew layer
├── DESIGN-NOTES.md              # known limits, and why docs are text in git
├── skills/                      # one folder per command in Usage
├── references/                  # mechanics shared by more than one skill
├── hooks/hooks.json             # 5 deterministic warn-only hooks
├── scripts/
│   ├── docs_*                   #   validate, scaffold, render, close, archive,
│   │                            #   profile, detect, feedback
│   ├── crew_*                   #   crew scaffold, knobs, CLAUDE.md snippet, crew_test.sh
│   └── hook_*                   #   one .sh wrapper + one .py worker per hook
├── templates/
│   ├── docs/                    #   the full 17-folder tree; a profile takes a subset
│   ├── crew/                    #   scripts/crew, role commands, operating docs
│   └── claude-md-snippet.md     #   the docs block for CLAUDE.md
├── design/                      # design system + generated samples — never hand-edit
├── briefs/                      # gitignored: brief output in a repo without docs/
├── CHANGELOG.md
├── LICENSE
└── README.md
```

**Invariants** — do not "fix" these away:

- The three-layer order is fixed, and only a Decision amends Architecture.
- Exactly two skills are reachable by Claude on its own (`brief` and `explain`);
  the rest carry `disable-model-invocation: true`. The number in **Requirements**
  is the budget that buys.
- Hooks stay deterministic and warn-only by default; the rationale comments in
  `scripts/hook_*` are load-bearing.
- Writes to user config (`CLAUDE.md`) happen only after an explicit yes.
- Templates stay project-agnostic — never inject a project name into them.
- `STANDARD.md` is the source of truth; validator, templates and skills stay 1:1
  with its §4 frontmatter contracts.

</details>

---

## 🗺 Roadmap

- **Blocking hooks**, once real projects show the triggers rarely misfire.
- **A cross-repo view**: every figure is scoped to one repo today
  ([DESIGN-NOTES §2.8](DESIGN-NOTES.md)).
- **More evidence for `owns` profiles**: two more repos where `NOTE [profile]`
  never cries wolf.
- **Beyond Claude Code**: the model and the scripts are agent-neutral, and only
  the packaging is not.
