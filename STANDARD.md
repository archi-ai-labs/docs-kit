# docs-kit STANDARD — the three-layer docs model

This file is the **source of truth** for the docs-kit plugin. Every skill, command,
hook, template, and the validator conform to this document. Target repos get a
30-second digest of it as `docs/README.md`; when the digest and this file disagree,
this file wins.

The model below is fixed. Do not add stages, remove stages, or reorder them.

## 1. The three layers

```
LAYER 1 — FOUNDATION (state; only a Decision may amend it)
  Products → Roadmap → Architecture

LAYER 2 — CHANGE (process; fully traceable)
  Issue (status: exploring | open | promoted | archived)
    ├─ exploring = raw research, not yet a real Issue
    ├─ FAST lane (no Architecture change AND revert < 1 day)  → straight to Backlog
    └─ FULL lane (touches Architecture, or hard to reverse,
                  or > 1 day of work)                          → Proposal → Decision → Backlog
  Review — periodic audit. READ-ONLY: it never edits layer 1 or layer 2,
           it only appends findings to the audit log.

LAYER 3 — OPERATIONAL REFERENCE (edit directly; no Decision required)
  Conventions, Services, Runbooks, Deploy, FE-integration, QA
```

Layer rules:

- **Layer 1** is state, not history. It describes what the product/roadmap/architecture
  *is*. Architecture may only change through an approved Decision, recorded in the
  `amended_by` list. Products and Roadmap are kept aligned with approved Decisions.
- **Layer 2** is the only path by which layer 1 changes. Every change is traceable:
  Backlog → Decision → Proposal → Issue (full lane) or Backlog → Issue (fast lane).
- **Layer 3** is reference material for operating the system. Edit it directly.
  No traceability fields, no Decision needed.
- **Review (`92_audit/`)** observes layers 1–2 and appends findings. It never edits them.

## 2. Folder layout (14 folders under `docs/`)

| # | Folder | Type | Layer |
|---|--------|------|-------|
| 00 | `00_roadmap` | Roadmap | 1 |
| 01 | `01_products` | Products | 1 |
| 02 | `02_architecture` | Architecture | 1 |
| 20 | `20_issues` | Issue | 2 |
| 21 | `21_proposals` | Proposal | 2 |
| 22 | `22_decisions` | Decision | 2 |
| 23 | `23_backlog` | Backlog | 2 |
| 30 | `30_conventions` | Conventions | 3 |
| 40 | `40_services` | Services | 3 |
| 50 | `50_runbooks` | Runbooks | 3 |
| 60 | `60_fe-integration` | FE-integration | 3 |
| 70 | `70_deploy` | Deploy | 3 |
| 92 | `92_audit` | Review | oversight |
| 93 | `93_qa` | QA | 3 |

## 3. IDs and references

- ID format: `ISSUE-001`, `PROPOSAL-001`, `DECISION-001`, `BACKLOG-001` —
  type prefix + sequential, zero-padded, three digits minimum.
- The ID lives in frontmatter `id:`. **File names are never reference keys** —
  a file may be renamed freely; only `id:` matters.
- All `*_ref:` frontmatter fields (`issue_ref`, `proposal_ref`, `source_ref`, …)
  must contain an `id:` that exists somewhere under `docs/`.
- Next ID of a type = highest existing number of that type + 1.
- IDs numbered `000` are reserved for the example chain shipped by `docs-init`.
  Real documents start at `001`. Delete the four `-000` example files together
  (they reference each other) or keep them as a format reference.

## 4. Frontmatter contracts (enforced by the validator)

Values may be followed by an inline ` # comment` (stripped before checks).
Quote values with double quotes or not at all — the validator strips `"` only.
The validator checks key **presence** for every field listed below, plus the
enum values and ID prefixes noted. `README.md` files inside typed folders are
exempt.

### `01_products/*.md` — Product
```yaml
---
name: ""            # product name
users: ""           # who uses it
problem: ""         # the problem it solves
scope_in: []        # what is in scope
scope_out: []       # what is explicitly out of scope
success_metric: ""  # how success is measured
---
```

### `02_architecture/*.md` — Architecture
```yaml
---
components: []      # main components; detail in body
data_flow: ""       # one-line summary; detail in body
tech_stack: []
constraints: []
amended_by: []      # ONLY the Decision workflow appends entries here.
                    # Entry format: "- YYYY-MM-DD DECISION-NNN <summary>"
---
```
Each `amended_by` entry must contain a `DECISION-NNN` token that resolves to an
existing Decision `id:`.

### `20_issues/*.md` — Issue (id prefix `ISSUE-`)
```yaml
---
id: ISSUE-001
description: ""     # what this is about
why: ""             # why it is worth doing
lane: fast          # fast | full  (see §5)
status: exploring   # exploring | open | promoted | archived
---
```

### `21_proposals/*.md` — Proposal (id prefix `PROPOSAL-`)
```yaml
---
id: PROPOSAL-001
issue_ref: ISSUE-001
problem: ""         # restated problem
proposed: ""        # the proposed option (one line; detail in body)
impact: ""          # impact on Architecture / Roadmap ("none" if none)
---
```
The body **must** contain a heading `Alternatives considered` listing 2–3
options with trade-offs (the validator greps for this heading).

### `22_decisions/*.md` — Decision (id prefix `DECISION-`)
```yaml
---
id: DECISION-001
proposal_ref: PROPOSAL-001
outcome: approved   # approved | rejected
reason: ""          # why approved / rejected
decided_by: ""      # who decided
architecture_amendment: none   # optional field. "none", or a one-line summary of
                               # the Architecture amendment this Decision mandates
---
```
If `outcome: approved` and `architecture_amendment` is a real summary (not
`none` / empty), `02_architecture/` must be amended **in the same session**
(body updated + `amended_by` entry appended).

### `23_backlog/*.md` — Backlog (id prefix `BACKLOG-`)
```yaml
---
id: BACKLOG-001
description: ""     # the work item
source_ref: DECISION-001   # Decision if full lane, Issue if fast lane. Never empty.
status: open        # open | in-progress | done
---
```

### `92_audit/` — Review / audit log (append-only)
No frontmatter. One line per event, **appended at the end of the file, never
inserted, edited, or deleted** (validated against git HEAD). Line format:

```
YYYY-MM-DD | what happened | ref (IDs or "-") | deviation from Decision/Backlog ("-" if none) | why
```

### Layer 3 folders (`30/40/50/60/70/93`) — Reference
No traceability fields, no required frontmatter. Free-form content on the
folder's topic. The validator does not check these folders.

`00_roadmap/` has no required frontmatter either; keep it aligned with
approved Decisions.

## 5. Lane rule — two questions

Ask both. **Any "yes" → FULL lane. Both "no" → FAST lane.**

1. Does this change modify the Architecture doc?
2. If it turns out wrong, would reverting take more than 1 day?

- FAST lane: `Issue → Backlog` (`source_ref` = the Issue).
- FULL lane: `Issue → Proposal → Decision → Backlog` (`source_ref` = the Decision).

## 6. Mandatory triggers (the agent must follow these)

| Session event | Required docs action |
|---|---|
| Code change touches a schema, API contract, or component boundary | A Decision must already exist. If none exists: create an Issue, stop, and ask the user. |
| A Backlog item is completed | Set its `status: done` and append one line to `92_audit/`. |
| A Decision is approved | Amend `02_architecture/` in the SAME session (body + `amended_by` entry). |
| Starting work that is not in the Backlog | Create an Issue before writing code. |

## 7. Validator contract (`scripts/docs_validate.sh`)

Deterministic, read-only, no LLM, no network. Usage:
`docs_validate.sh [docs_dir]` (default `./docs`).

Checks:

| Tag | Check |
|---|---|
| `[ref]` | Every `*_ref:` value resolves to an existing `id:` under docs/. Duplicate `id:` values are also reported here. |
| `[backlog]` | Every Backlog item has a non-empty `source_ref:`. |
| `[frontmatter]` | Required fields per type (§4) are present; `lane`/`status`/`outcome` enums are valid; `id:` prefixes match their folder; Proposals contain an "Alternatives considered" heading. |
| `[audit-append]` | `92_audit/` files are append-only vs git HEAD (no deleted or rewritten lines). Skipped when git or HEAD is unavailable. |
| `[amended-by]` | Every `amended_by` entry in Architecture contains a `DECISION-NNN` token that resolves to an existing Decision. |

Output: one line per violation — `FAIL [tag] <file>: <message>` — then a count.
Exit codes: `0` clean, `1` violations found, `2` setup error (e.g. docs/ missing).

The validator checks **form, not content**. It is the source of truth for form:
skills never "eyeball-validate" in its place.

## 8. Enforcement hooks (warn-only, deterministic)

Two hooks, both plain scripts, **no LLM calls**:

1. **PostToolUse** on `Edit|Write`: if the edited path is under
   `docs/02_architecture/` → warn (user + agent): "Architecture is amended only
   via the Decision workflow — confirm a Decision ref exists."
2. **Stop**: scan the session transcript. If files matching sensitive patterns
   were edited but the session never created or referenced any Issue/Decision →
   remind the user to run `/docs-kit:docs-sync`.

**Why warn-only:** these rules have not been battle-tested across real projects
yet. Blocking on a false positive teaches users to disable the hook entirely,
which loses all enforcement. Warn now; promote to block only after the trigger
rules have been tuned in practice.

Hooks are silent in repos that do not use docs-kit (no `docs/` skeleton).

## 9. Configuration — `.docs-kit.json` (optional, in the target repo root)

```json
{
  "sensitive_paths": ["**/schema/**", "**/api/**", "**/migrations/**"]
}
```

`sensitive_paths` overrides the default patterns used by the Stop hook.
Patterns are matched with fnmatch against the repo-relative path; a leading
`**/` also matches at the repo root. Paths under `docs/` are never treated as
sensitive-zone code.

## 10. Generated HTML views (read models)

`scripts/docs_render.sh` (→ `docs_render.py`, Python 3.9 stdlib, no LLM, no
network) generates three self-contained pages into `docs/`, styled per
`design/design-system.html` ("change-control print"):

| Page | Content |
|---|---|
| `docs/index.html` | Menu beside README.md: system map (clickable), sheet cards, Layer-3/Oversight listing, the one hard rule |
| `docs/current.html` | Layer 1: product cards, roadmap board, components, data-flow graph, constraints, revision block |
| `docs/changes.html` | Layer 2: issue/backlog boards, proposal & decision tables, trace chains, audit table |

Rules:

- **Read model only.** The renderer never edits markdown; the markdown stays
  the source of truth. Generated pages carry a `GENERATED` header comment —
  never hand-edit them; regenerate with `/docs-kit:docs-render`
  (docs-init creates them, docs-sync refreshes them).
- **Deterministic.** Same input docs → same output bytes; only the
  generated-at stamp moves (override with `DOCS_KIT_NOW=<ISO>` for
  reproducible output). Files sorted by name; logs newest-first.
- **Data-flow syntax** (one edge per line in `data_flow`):
  `a -> b` sync · `a ~> b` async (teal, dashed) · `a -> b : label` edge label.
  Component entries may annotate a kind — `postgres [db]`, `jobs [queue]`,
  `dashboard [ui]` — which sets the node icon/tint; unannotated entries are
  services; nodes absent from `components` are drawn dashed as external.
  Branching flows render as a layered graph (longest-path layering,
  alphabetical within a column); >12 nodes → one figure per connected flow
  group; unparseable or cyclic flows fall back to text — never a guessed
  diagram.
- **Colour (the hue budget).** Four hue families, spent by meaning and never for
  decoration: blue = Layer 1 · violet = Layer 2 · teal = the fast-lane bypass ·
  orange = interactive or happening right now. Green and red are stamped
  verdicts only. A reference tag takes the hue of the layer it sends you *to*;
  section marks and board column rules follow the same rule (the live column
  takes orange, a shelved one goes grey). Anything with no layer — a git rev, a
  timestamp, a tool version — stays graphite, and prose, tables, and body copy
  never take a hue at all. Each sheet opens with a 3px `hue-rule` strip drawn to
  scale from its own real counts.
- **Motion (pure CSS, zero JS).** Exactly three meaning-bearing animations:
  a white packet gliding along solid edges (data direction), marching dashes on
  dashed strokes (async / fast-lane / amendment), and an LED pulse on live dots
  (orange = in-progress, green = docs-check clean). No entrance or hover
  animations; `prefers-reduced-motion` disables all of it.
- The validator ignores `docs/*.html` (it only reads `.md`); check 4's
  append-only rule is unaffected.

## 11. Language — English frame, Vietnamese explanation

Two roles, deliberately split. **Structure is English; explanation is Vietnamese.**

English, always — these are names, not prose, and translating them would break
either the validator or the reader's ability to grep:

| what | examples |
|---|---|
| folder + file names | `20_issues/`, `architecture.md` |
| frontmatter field names | `status`, `lane`, `source_ref`, `amended_by` |
| enum values | `open`, `in-progress`, `done`, `approved`, `rejected`, `fast`, `full` |
| id prefixes | `ISSUE-`, `PROPOSAL-`, `DECISION-`, `BACKLOG-` |
| domain terms | Issue, Proposal, Decision, Backlog, Architecture, fast lane, full lane |
| UI labels in the rendered views | section headings, table headers, status text, stamps, `NO PRODUCTS` |
| roadmap column headings | `## Now`, `## Next`, `## Later`, `## Not doing` |

Vietnamese — everything whose job is to *explain*: descriptions, problem
statements, rationale, scope lines, audit entries, and every lede, note, figure
caption and empty-state hint in the generated views.

Rules:

- **English terms stay bare inside Vietnamese sentences** — no translation, no
  gloss in parentheses, no bold. "Chỉ được sửa qua Decision workflow", not
  "Chỉ được sửa qua quy trình Quyết định (Decision workflow)". Bold already
  carries two meanings in these views (the redline pen `.hl`, and author `**`),
  so it is not available as a third signal for "this word is English".
- **Every `<h2>` in the generated views carries one Vietnamese gloss line**
  (`.h2sub`) under the English heading — one line, no full stop.
- **Roadmap headings are labels, so they stay English**, but `roadmap_kind()`
  also accepts the obvious Vietnamese equivalents. The failure it guards against
  is silent: an unrecognised heading loses its column colour without any error.
- **A document's title may be Vietnamese; its file name may not.** `name:` is
  explanation and gets translated — `name: "Đối soát giao dịch"`. The file it
  lives in stays ASCII — `reconciliation.md`. File names are keys, not prose:
  they appear in shell commands, git output, and URLs, and §3 already makes them
  non-referential, so there is nothing to gain by translating them.
- **Anchor slugs fold diacritics anyway** (`slugify()`), and dedupe within a
  page. Nothing enforces the rule above, and the failure it prevents is quiet:
  a plain `[^a-z0-9]` filter would collapse both `phân-quyền` and `phần-quyền`
  to one HTML id, so the sidebar link would open the wrong document.
- `<html lang="vi">`, since the prose dominates the page.
