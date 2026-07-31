# docs-kit

[![validate](https://github.com/archi-ai-labs/docs-kit/actions/workflows/validate.yml/badge.svg)](https://github.com/archi-ai-labs/docs-kit/actions/workflows/validate.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-8A63D2.svg)](https://docs.claude.com/en/docs/claude-code)

> A **Claude Code plugin** that gives a repo a documentation model with a spine:
> three layers, one direction of change, and deterministic checks that hold it
> together — plus an HTML read model generated straight from the markdown.

Project docs rot in a specific way: the architecture doc drifts from the code,
nobody can say which decision caused which change, and the whole thing quietly
becomes fiction. `docs-kit` fixes the direction of change instead of asking people
to be disciplined — **Architecture is amended only through a Decision**, every
change traces back to an Issue, and the audit log is append-only. What a machine
can check, a script checks; what it cannot, a warn-only hook reminds you about.

**Requirements:** Claude Code — **v2.1.154 or later** to get the opt-in install
described below; earlier versions install this plugin switched on.
`/docs-kit:docs-render` additionally wants **Python 3.9+** — if it is missing, the
renderer skips with a message and nothing else breaks. Scripts hold a **bash 3.2
/ BSD awk** floor, so they run on a stock macOS shell.

**Always-on context cost: about 77 tokens** — one skill description, the only
thing here Claude can reach on its own. The other four load nothing until you
type them.

**Menu:** [Install](#-install) · [Usage](#-usage) · [The model](#-the-model) · [Generated views](#-generated-views) · [Enforcement](#-enforcement) · [Uninstall](#-uninstall) · [For maintainers](#-for-maintainers) · [Roadmap](#-roadmap)

---

## 🚀 Install

Two ways to install — a one-line terminal command, or from inside Claude Code.
**Option 1 is recommended.**

### Option 1 — One command in your terminal ⭐

Installs globally in your **user** settings (`~/.claude/settings.json`), so it's
active in every project. Paste this in:

```bash
curl -fsSL https://archi-ai-labs.github.io/agent-marketplace/install.sh | bash -s -- --plugins docs-kit
```

`--plugins docs-kit` is not optional here: with no arguments the installer
registers the catalog and enables only `trim-kit`, because `docs-kit` installs
hooks and nothing should switch hooks on for you unasked. Naming it *is* that
decision, so this route leaves the plugin **on** — you can skip step 3 below.

Want it in **one project only** instead? Add `--project` — it writes
`./.claude/settings.json` in the current folder rather than your home config:

```bash
curl -fsSL https://archi-ai-labs.github.io/agent-marketplace/install.sh | bash -s -- --plugins docs-kit --project
```

Either way it's safe to re-run: it backs up your existing `settings.json` first and
aborts without touching it if the JSON is invalid.

### Option 2 — Inside Claude Code (Windows / no bash)

No terminal or `bash` needed — run these from a Claude Code session, works everywhere:

```
/plugin marketplace add archi-ai-labs/agent-marketplace
/plugin install docs-kit@archi-ai-labs
```

The `/plugin install` step **does not default to global** — it opens a scope picker.
Choose:

- **User** — every project (same as Option 1) → **pick this for global**
- **Project** — this repo, shared with collaborators (`.claude/settings.json`)
- **Local** — this repo, just you (`.claude/settings.local.json`)

> Want global with no picker? Run the shell command
> `claude plugin install docs-kit@archi-ai-labs` — it installs to **User** scope
> (global) unless you pass `--scope`.

### ▶︎ After installing (either option)

1. **Restart** Claude Code (or run `/reload-plugins`) — it fetches the plugin from GitHub.
2. If asked to **trust** the `archi-ai-labs` marketplace, approve it once. ✅
3. **Turn it on if you came via Option 2** — that route installs the plugin
   *disabled*:
   ```
   /plugin enable docs-kit@archi-ai-labs
   ```
4. Run **`/docs-kit:docs-init`** in the repo you want documented.

> **Why step 3 exists, and why Option 1 skips it.** `docs-kit` registers two
> hooks, `PostToolUse` and `Stop`. Hooks run without you asking on that
> particular occasion, so the plugin ships `defaultEnabled: false` and nothing
> switches them on for someone who has not decided to have them. Option 1 makes
> you name `--plugins docs-kit`, which is that decision — the installer writes an
> explicit `true` into `enabledPlugins`, and an explicit setting outranks the
> default. Option 2's `/plugin install` does not ask, so it lands disabled.
>
> **Already using `docs-kit` before v0.9.0? Nothing changes for you.** A choice
> already recorded in your settings outranks this default at every scope. And on
> Claude Code older than **v2.1.154** the field is ignored entirely and the
> plugin installs enabled either way.

<details>
<summary><b>Extras</b> — read the script first · local dev · what the installer writes</summary>

### Prefer to read the script before running it?

Piping `curl` into `bash` runs code sight unseen. To inspect it first:

```bash
curl -fsSL https://archi-ai-labs.github.io/agent-marketplace/install.sh -o install.sh
less install.sh   # review
bash install.sh --plugins docs-kit   # then run
```

### Local dev — try it without installing

Fastest loop while editing the plugin — a session-only load, nothing written to
your settings:

```bash
claude --plugin-dir /path/to/docs-kit
```

### What the installer actually writes

The install script (Option 1) deep-merges these two keys into the target
`settings.json` — you can add them by hand instead of running the script:

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

`extraKnownMarketplaces` pre-registers the marketplace; `enabledPlugins` turns the
plugin on by default.

</details>

---

## 💡 Usage

| Command | What it does | Writes files |
|---|---|---|
| `/docs-kit:docs-init` | Scaffold 15 folders + templates into `docs/`, read the repo's source to fill Architecture, and optionally wire the rules into `CLAUDE.md`. Refuses to touch an existing `docs/`; asks before every write outside the scaffold. | Yes |
| `/docs-kit:docs-sync` | End-of-session reconcile: backlog statuses, audit entries, retroactive Issues, pending Architecture amendments, architecture-vs-code drift. | Yes |
| `/docs-kit:docs-check` | Run the deterministic validator and explain each failure. Never fixes. | No |
| `/docs-kit:docs-render` | Generate/refresh the HTML views of `docs/`. Deterministic; never edits markdown. | Yes (HTML only) |
| `/docs-kit:brief` | Turn settled decisions into a delegation prompt for a coding agent — gates on a decision-freeze check first. In a repo that has `docs/`, also records the work as an Issue and routes it through Layer 2 before writing the prompt. The one skill Claude may invoke on its own. | Yes (`docs/`, only after you confirm) |

**Typical flow:** `docs-init` once → work → `docs-sync` at the end of a session →
`docs-check` whenever you want the structure verified.

```text
$ /docs-kit:docs-init
  → scaffolds docs/, reads the source, renders the HTML views
$ …work…
$ /docs-kit:docs-sync
  → flips backlog statuses, appends audit lines, flags undocumented drift
```

---

## 🧭 The model

```
LAYER 1 — FOUNDATION   Products → Roadmap → Architecture       (state; only Decisions amend)
LAYER 2 — CHANGE       Issue → [Proposal → Decision] → Backlog (process; traceable)
LAYER 3 — REFERENCE    Conventions/Services/Runbooks/Deploy/FE/QA (edit directly)
OVERSIGHT              92_audit — append-only audit log
```

Two lanes run through Layer 2. The **fast lane** goes `Issue → Backlog` directly;
the **full lane** requires a Proposal and a Decision. The test is two questions:
does it modify the Architecture doc, and would reverting it take more than a day?
Either answer being yes puts the change in the full lane.

The full model lives in **[STANDARD.md](STANDARD.md)** — the source of truth every
skill, hook, script, and template conforms to. Frontmatter contracts (§4), the
validator contract (§7), the generated views and figure standard (§10), and the
language split (§11) are specified there, not left to habit.

---

## 🖼 Generated views

`/docs-kit:docs-render` builds a small read-only site from the markdown — same
input, same output bytes, no LLM and no network:

| Page | Content |
|---|---|
| `docs/index.html` | Menu beside README: system map, sheet cards, Layer-3 listing, the one hard rule |
| `docs/current.html` | Layer 1 — product cards, roadmap board, component cards, data-flow figure, business-flow sequences, revision block |
| `docs/changes.html` | Layer 2 — issue/backlog boards, proposal & decision tables, trace chains, audit table |

Real output is committed under [`design/`](design/) as the reference for what the
renderer produces — [`sample-current.html`](design/sample-current.html) is the most
representative. The samples are regenerated from a fixture, never hand-edited, and
CI fails if they drift.

Two rules worth knowing before you write a flow. **A figure is never shrunk to
fit** — one wider than the column scrolls instead, because text scaled down to
make a diagram fit is a diagram nobody reads. And **`data_flow` is always a
graph**: a cycle is not a drawing problem but a callback or a cache read-back, so
those edges are lifted out for layering and drawn back in on return lanes below
the rows. Past the density budget (20 nodes · 32 edges · 10 per column) the graph
is still drawn in full — it just scrolls, and a note suggests splitting the flow
across Architecture docs. The complete edge table sits under every figure. See
STANDARD §10.

---

## 🔒 Enforcement

Two hooks, both **deterministic, warn-only, and silent in repos without a `docs/`
skeleton**. No LLM runs inside a hook.

- **PostToolUse** (Edit/Write) — editing `docs/02_architecture/` or
  `docs/03_business-logic/` prints a reminder that layer 1 is amended only via the
  Decision workflow. `templates/docs/` is exempt, so the plugin's own tree is quiet.
- **Stop** — if the session edited sensitive paths (default `**/schema/**`,
  `**/api/**`, `**/migrations/**`; override via `.docs-kit.json` in the repo root)
  without creating or referencing any Issue or Decision, it suggests
  `/docs-kit:docs-sync`.

Warn-only by design: these rules have not been battle-tested across enough real
projects, and a false positive that *blocks* teaches people to disable hooks
entirely — which loses all enforcement. Promote to blocking only after the
triggers have been tuned in practice.

---

## 🧹 Uninstall

From inside Claude Code:

```
/plugin uninstall docs-kit@archi-ai-labs     # remove the plugin
/plugin marketplace remove archi-ai-labs     # also drop the catalog (optional)
```

- **Just turn it off** without removing: `/plugin disable docs-kit@archi-ai-labs`
- Run `/reload-plugins` (or restart Claude Code) to apply.

> Removing the marketplace uninstalls every plugin you installed from it — so if
> `docs-kit` was your only one, `marketplace remove` alone is enough.

**Installed with the script (Option 1)?** You can instead undo it by deleting the
two keys the installer added — `extraKnownMarketplaces["archi-ai-labs"]` and
`enabledPlugins["docs-kit@archi-ai-labs"]` — from your `settings.json`. The
installer left a timestamped `.bak` copy next to it to restore from.

Uninstalling removes the plugin, not your docs — `docs/` is ordinary markdown in
your repo and keeps working without it.

---

## 🛠️ For maintainers

<details>
<summary><b>Validate before sharing</b></summary>

```bash
claude plugin validate .    # manifest + skill frontmatter
```

That, and the full test recipe, run automatically on every push and PR via
[`.github/workflows/validate.yml`](.github/workflows/validate.yml): tag-vs-version,
manifest JSON, script syntax on python 3.9 (the portability floor), a fresh
scaffold validating clean, the validator still rejecting a dangling ref, both
hooks, and `design/sample-*.html` matching a fresh render.

</details>

<details>
<summary><b>Test recipe</b> — what to run by hand</summary>

```bash
# scaffold into a scratch repo and validate it
work="$(mktemp -d)"; git -C "$work" init -q
bash scripts/docs_scaffold.sh "$work"
bash scripts/docs_validate.sh "$work/docs"     # arg is the DOCS dir, not the repo root

# render, reproducibly
DOCS_KIT_NOW=2026-07-31T09:30:00 python3 scripts/docs_render.py "$work"

# regenerate the design samples — must produce no diff
bash design/make-samples.sh && git diff --stat -- design/
```

Mutating a ref, an enum, an audit line, or an `amended_by` entry must turn the
validator's `OK` into `FAIL` lines — a validator that only ever passes is not a
test.

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

Subscribers pick up the new version on their next `/plugin marketplace update`
(or a session restart).

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
├── STANDARD.md                  # source of truth for the model
├── skills/                      # all five commands: docs-init (entry point),
│                                #   docs-sync, docs-check, docs-render, brief
├── references/                  # mechanics shared by more than one skill
│   └── issue-capture.md         #   creating an Issue — read by brief + docs-sync
├── hooks/hooks.json             # 2 deterministic warn-only hooks
├── scripts/                     # docs_validate.sh, docs_scaffold.sh, docs_render.{sh,py}, hook workers
├── design/                      # "change-control print" design system + generated samples
│   ├── design-system.html       #   the design contract
│   ├── sample-*.html            #   real renderer output — regenerate, never hand-edit
│   └── fixture/ + make-samples.sh
├── templates/                   # the 15-folder docs tree + CLAUDE.md snippet
├── CHANGELOG.md
├── LICENSE
└── README.md
```

`commands/` is gone as of v0.9.0. Three of its five files were six-line wrappers
that only said *"invoke the same-named skill"* — and a skill outranks a command
of the same name, so those three never ran. The other two, `brief` and
`docs-render`, held real content and became skills. Nothing about typing
`/docs-kit:<name>` changed.

**Invariants** — do not "fix" these away:

- The three-layer order is fixed, and only a Decision amends Architecture.
- Exactly one skill is reachable by Claude on its own (`brief`); the rest carry
  `disable-model-invocation: true`. The number in **Requirements** is the budget
  that buys.
- Hooks stay deterministic and warn-only; the rationale comments in
  `scripts/hook_*` are load-bearing.
- Writes to user config (`CLAUDE.md`) happen only after an explicit yes.
- Templates stay project-agnostic — never inject a project name into them.
- `STANDARD.md` is the source of truth; validator, templates and skills stay 1:1
  with its §4 frontmatter contracts.

</details>

---

## 🗺️ Roadmap

- **Blocking enforcement, once the triggers have earned it.** The hooks warn today
  because the rules are young. The path to blocking runs through false-positive
  data from real projects, not through confidence.
- **More read models from the same markdown.** The renderer gained business-flow
  sequences in 0.7.0; domain state machines (`order: new → open → filled`) are the
  obvious next figure, since they answer a question no static component map can.
- **Beyond Claude Code.** The three-layer model, the lane test and the validator
  are plain markdown and POSIX scripts — none of that is Claude-specific. Only the
  packaging (skills, commands, hooks) is, so another agent would need a new
  wrapper around the same `scripts/` and `templates/`.
