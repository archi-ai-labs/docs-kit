# docs-kit STANDARD — the three-layer docs model

This file is the **source of truth** for the docs-kit plugin. Every skill, command,
hook, template, and the validator conform to this document. Target repos get a
30-second digest of it as `docs/README.md`; when the digest and this file disagree,
this file wins.

The model below is fixed. Do not add stages, remove stages, or reorder them.

How approved work *runs* — worktrees, parallel sessions, locks, the merge
procedure — is governed by `EXECUTION.md`, the execution layer's own source of
truth. The two files freeze at different speeds: this model is fixed, that
layer is still learning.

## 1. The three layers

```
LAYER 1 — FOUNDATION (state; only a Decision may amend it)
  Products → Roadmap → Architecture → Business logic → API contracts

LAYER 2 — CHANGE (process; fully traceable)
  Issue (status: exploring | open | promoted | archived)
    ├─ exploring = raw research, not yet a real Issue
    ├─ FAST lane (all three §5 questions "no")                → straight to Backlog
    └─ FULL lane (touches Architecture, hard to reverse,
                  or an irreversible side effect)              → Proposal → Decision → Backlog
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

## 2. Folder layout (up to 17 folders under `docs/`)

Twelve of these are **core** and every repo gets them. Five are conditional on what
the repo declares it owns, and a repo that declares nothing gets all seventeen — the
full map, and the reasoning for it, is §9.1.

| # | Folder | Type | Layer | Present when |
|---|--------|------|-------|---|
| 00 | `00_roadmap` | Roadmap | 1 | always |
| 01 | `01_products` | Products | 1 | always |
| 02 | `02_architecture` | Architecture | 1 | always |
| 03 | `03_business-logic` | Business logic | 1 | always |
| 04 | `04_api` | API contract | 1 | `owns: endpoints` |
| 20 | `20_issues` | Issue | 2 | always |
| 21 | `21_proposals` | Proposal | 2 | always |
| 22 | `22_decisions` | Decision | 2 | always |
| 23 | `23_backlog` | Backlog | 2 | always |
| 30 | `30_conventions` | Conventions | 3 | always |
| 40 | `40_services` | Services | 3 | `owns: deploys` |
| 50 | `50_runbooks` | Runbooks | 3 | `owns: deploys` |
| 60 | `60_fe-integration` | FE-integration | 3 | `owns: screens` |
| 70 | `70_deploy` | Deploy | 3 | `owns: deploys` |
| 92 | `92_audit` | Review | oversight | always |
| 93 | `93_qa` | QA | 3 | always |
| 99 | `99_feedback` | Kit feedback | oversight | always |

### `_archive/` — terminal documents leave the hot set

Each layer 2 folder may hold an `_archive/` subfolder. A document moves there once
it can no longer change: a Backlog item at `done` with its audit line written, a
Proposal or Decision whose chain has completed, and an Issue that is either at
`archived` or has outlived every successor it produced.

**An Issue leaves two ways, and only one of them is a declaration.** `archived` says a
person dropped it. The other is derived exactly as the Decision's is: an Issue at
`promoted` is terminal once the Proposal citing it (full lane) and every Backlog item
citing it (fast lane) are terminal themselves, and an Issue that fed both needs both.
An Issue at `promoted` with no successor at all is never archived — that is a broken
chain, not a finished one, and the least-read folder is the worst place to put it.
Before 0.29.0 only the declaration existed, which meant `20_issues/` shrank when work
was abandoned and grew when it succeeded.

**Archiving lowers read cost. It never lowers the standard a document is held to.**
The validator walks `_archive/` exactly as it walks the folder above it — ids are
collected, refs must still resolve, frontmatter is still checked. Skills read it only
when an id points there.

Moving a file is safe because §3 already guarantees it: file names are not reference
keys. Use `git mv` so the history follows. Layer 1 is state, not history — it is never
archived; a component that no longer exists is removed by a Decision, not filed away.

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

The body may carry one or more ```` ```flow ```` blocks — the product's business
flows, rendered as sequence figures (see §10). One block per scenario:

````markdown
```flow
title: Đặt lệnh limit
trigger: POST /orders với idempotency key
code: src/engine/match.go
api -> engine : validate payload, kiểm tra key trùng
engine -> risk : còn đủ margin không
engine -> engine : khớp vào order book
engine ~> audit : append trade event
outcome: lệnh nằm trên sổ, tiền đã bị giữ
```
````

### `02_architecture/*.md` — Architecture
```yaml
---
components: []      # "name [kind] `path/in/repo` — what it does"
data_flow: []       # "a -> b : label" per entry; "~>" for async
tech_stack: []
constraints: []
amended_by: []      # ONLY the Decision workflow appends entries here.
                    # Entry format: "- YYYY-MM-DD DECISION-NNN <summary>"
rejected: []        # optional. ONLY the Decision workflow appends entries here.
                    # Entry format: "- DECISION-NNN <what was ruled out>"
verified_at: ""     # optional. The git rev at which the paths below were last read.
---
```
Each `amended_by` entry must contain a `DECISION-NNN` token that resolves to an
existing Decision `id:`. `rejected` follows the same rule.

**`rejected` exists so that "what was already considered and dropped" is answerable
from layer 1 alone.** A Decision with `outcome: rejected` records information that
appears nowhere else in layer 1 — the architecture doc says what the system *is*, never
what it deliberately is not. Without this field the only way to find out is to read
every Decision, which is a cost that grows forever to produce an answer that does not.
Both fields are optional: a repo scaffolded before they existed stays valid.

**`verified_at` is the anchor for staleness.** It holds the git rev at which someone
last actually read the paths this document names. The validator diffs that rev against
the working tree and reports how many of those paths have moved since. See §7.

#### One architecture document per service

`02_architecture/` is a folder, not a file. A repo with one deployable keeps one
`architecture.md`; a repo with several keeps one document per service — `orders.md`,
`billing.md` — and each describes **only what that service owns**: its components, the
tables in its own ```` ```erd ````, its own contracts in ```` ```class ````.

This is the same rule the ERD was always following by accident. A schema is only
correct when it is scoped to its owner; a single fence holding every service's tables
blows the budget in §10 and, worse, says nothing about who owns what.

Four placements make the split reconstructible rather than fragmentary:

| Fact | Whose document it belongs in |
|---|---|
| a component | the service that contains it |
| a table | the service that owns the writes |
| **an edge `a -> b`** | **`a` — the caller. A dependency is a property of the thing that has it.** |
| the contract behind that edge | `b` — the callee |

Put the edge in both and you have two sources for one fact, which is what the ERD's
derived cardinality and the component card's derived `role` both exist to avoid.

The renderer merges the folder back into one §3: one component list, one data-flow
graph, every ERD in document order, and each component card naming the document that
declares it. Nothing is authored twice, so nothing can disagree.

**Component names are reference keys and must be unique across the folder.**
`data_flow` edges name components, and the rendered cards resolve upstream and
downstream by name, so two documents declaring `store` make every edge touching it
ambiguous. The validator reports that under `[ref]`, exactly as it reports a duplicate
`id:`.

A component entry is one flat line — the validator reads frontmatter with awk,
so this grammar never nests:

```yaml
components:
  - engine `src/engine/match.go` — khớp lệnh limit/market, order book trong RAM
  - store [db] `deploy/pg/` — postgres, nguồn sự thật sau khi commit
```

`[kind]` is one of `db` · `queue` · `ui` · `svc` (default). The backticked path
is where the component lives in the source tree. The description states what the
component **is** — written after reading that code, not guessed from its name.
Longer explanation goes in a `### <name>` section in the body, which the
rendered card picks up as expandable detail.

The body carries ```` ```flow ```` blocks for scenarios, an ```` ```erd ```` block
for the data model this document's service owns, and a ```` ```class ```` block for
its types (all in §10).
Components answer *what exists* for services; the ERD answers the same question
for stored data and the class diagram for the code's own contracts, which is why
all three live here and not in folders of their own.

### `03_business-logic/*.md` — Business logic
```yaml
---
domain: ""          # what this rule set is about
amended_by: []      # ONLY the Decision workflow appends entries here.
rejected: []        # optional, same contract as Architecture's
verified_at: ""     # optional, same contract as Architecture's
---
```
Two required fields, and no more: adding an optional field later is cheap, removing
a required one breaks every repo already scaffolded — which is exactly why `rejected`
and `verified_at` arrived as optional.

The split against Architecture is by the question answered, not by subject:

| Question | Folder |
|---|---|
| What exists, and what calls what | `02_architecture/` |
| What the data looks like, and what links to what | `02_architecture/` (```` ```erd ````) |
| Doing X — what happens, in what order | `02_architecture/` (```` ```flow ````) |
| **Hitting condition Y — which way does it branch, by what rule** | **`03_business-logic/`** |
| **Where can this entity be, and what moves it** | **`03_business-logic/`** |

The body carries ```` ```flowchart ```` blocks for branching rules and
```` ```state ```` blocks for entity lifecycles (both in §10) and, for rules that
read better as a table than as a picture, plain markdown tables — a decision table
needs no grammar of its own.

`amended_by` entries follow the Architecture rule above: each must contain a
`DECISION-NNN` token that resolves to an existing Decision `id:`.

### `04_api/*.md` — API contract
```yaml
---
service: ""         # the component that publishes this contract
protocol: http      # http | grpc | graphql | event
base: ""            # optional. Base path, proto package, or topic prefix
generated_from: ""  # optional. Path to the artifact holding the volatile half
amended_by: []      # ONLY the Decision workflow appends entries here.
rejected: []        # optional, same contract as Architecture's
verified_at: ""     # optional, same contract as Architecture's
---
```

**This folder exists because §6 contradicted itself.** The trigger table has always
required a Decision before a code change touches an API contract, while the only place
a contract could live was layer 3 — where §4 says no Decision is needed. That was not a
gap in coverage; it was the standard demanding a Decision for a thing it gave nowhere
to record. An API contract is layer 1 state, so it is filed as layer 1.

`service:` **must name a component declared in `02_architecture/`.** That is the single
join between the two folders, and the validator enforces it: a contract attached to no
service is worse than no contract, because the boundary then looks documented and is
not. The check is skipped while the architecture declares no components at all.

The body carries one or more ```` ```api ```` blocks (§10) — and deliberately little
else. Status codes, field types and payload schemas do **not** belong here: they are the
volatile half, they are generated better than they are written, and a hand-copy of them
is stale within a sprint. Putting the volatile half behind the Decision gate is how a
gate gets routed around.

What lives here is the half no generator can state: which operations exist at the
boundary, what each one means, and what the service deliberately does **not** expose.
That changes rarely, which is exactly what makes it worth a Decision.

#### `generated_from` — the volatile half, read rather than maintained

Point it at the artifact the repo **already produces**: `openapi.json`, `*.proto`.
The renderer reads it at render time and prints the real operation list beside the
hand-written intent, marking each one:

| state | meaning |
|---|---|
| matched | in both — nothing to do |
| `artifact only` | **live and undocumented.** Per §6 adding it needed a Decision |
| `documented only` | the contract describes an operation the artifact does not ship |

The sync cost of that half is **zero**: nobody maintains it, it is re-read on every
render. That is precisely what makes the intent half above worth a Decision gate — the
part that changes often stopped being a document.

Gate it in CI:

```bash
docs_render.sh --check-api .     # 0 = match · 1 = drift, or the artifact is unreadable
```

An unreadable artifact fails too. A gate that quietly does not run is the failure this
gate exists to prevent.

Three constraints, each a consequence rather than a preference:

- **docs-kit consumes; it never generates.** Producing the artifact means knowing the
  framework, and the detector's discipline (§ `docs_detect.py`) is to read declared
  facts, never to infer them from a layout.
- **OpenAPI must be JSON.** The portability floor is python 3.9 *stdlib*: it has a JSON
  parser and no YAML one, and a hand-rolled YAML parser that misreads a contract is
  worse than one that refuses to read it. A `.yaml` path fails with that message rather
  than a guess.
- **Events are excluded from the comparison.** OpenAPI describes no events, so counting
  an `event` line as missing would make the check cry wolf on every correct contract.

Path parameters are normalised before comparison — `{id}`, `:id` and `[id]` are the
same operation, written by tools none of which is more correct; `[id]` is in the list
because Next.js and SvelteKit name route folders that way and copying the route path
into the contract is the obvious thing to do — and `base` is stripped from both sides, so a spec that puts `/v1` in `servers` and one that puts it in
every path describe the same API. The `generated_from` path is itself an anchor, so
`[anchor]` reports it the moment the artifact moves.

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

### `99_feedback/*.md` — a problem with the kit itself (id prefix `FEEDBACK-`)
One file per problem, and **the file is the prompt**: copy it whole into a
docs-kit session and the maintainer has everything. Fields are conventional, not
validated — `about` (`docs-kit` · `crew`), `kind` (`bug` · `doc` · `gap` ·
`friction`), `severity` (`silent` · `blocks` · `friction`), `status` (`open` ·
`sent` · `fixed`), plus the context `docs_feedback.sh` stamps in. Not indexed in
`INDEX.md`; not checked by the validator. Full rule in §12.

**No field here ends in `_ref`, deliberately.** A `*_ref` must resolve (§7), and a
report has to outlive the ticket that surfaced it — including the case where that
ticket is deleted. Mention an id in the body as ordinary prose instead.

## 5. Lane rule — three questions

Ask all three. **Any "yes" → FULL lane. All "no" → FAST lane.**

1. Does this change modify a layer 1 doc — Architecture, Business logic, or an API
   contract?
2. If it turns out wrong, would reverting take more than 1 day?
3. Is there an irreversible side effect — deleting data, publishing outside the
   repo, flipping a one-way flag, sending something to a person?

Question 3 outranks the other two: a rollback that takes 5 minutes restores
nothing that is already gone. (Added in 0.26.0; it only ever moves work *into*
the full lane, so no document that was valid before becomes invalid.) Repos
running the crew layer also declare a chosen fast lane in the reply itself —
the marker line and the gates around it live in `EXECUTION.md` §7.

- FAST lane: `Issue → Backlog` (`source_ref` = the Issue).
- FULL lane: `Issue → Proposal → Decision → Backlog` (`source_ref` = the Decision).

## 6. Mandatory triggers (the agent must follow these)

| Session event | Required docs action |
|---|---|
| Code change touches a schema, API contract, or component boundary | A Decision must already exist. If none exists: create an Issue, stop, and ask the user. The contract itself lives in `04_api/` — layer 1, so the same rule that demands the Decision now has somewhere to record its result. |
| Code change alters a branching business rule | Same — the rule lives in `03_business-logic/`, which is layer 1. |
| A Backlog item is completed | Set its `status: done` and append one line to `92_audit/`. Preferably by writing `Closes: BACKLOG-NNN` in the commit — see §6.1. In a crew repo, `crew done` performs the merge, the status flip and the worktree cleanup in one command (EXECUTION §6). |
| A Decision is approved | Amend `02_architecture/` in the SAME session (body + `amended_by` entry). |
| Starting work that is not in the Backlog | Create an Issue before writing code. |
| docs-kit or crew got it wrong — a script contradicted the standard, or finishing an ordinary task needed a workaround | File one report in `99_feedback/` (`docs_feedback.sh new <slug>`). §12 has the four cases that qualify and the four that do not. |

### 6.1 `Closes:` — letting the commit record the completion

A commit message may carry a git trailer naming what it finishes:

```
cache the roster lookup

Closes: BACKLOG-012
```

`scripts/docs_close.sh --apply` then sets `status: done` and appends the audit line,
citing the commit sha as the reason column.

This is not merely automation of a manual step; it changes what the audit trail
says. A line written from a session's own recollection cites the session, and the
session is gone. A line written from a trailer cites a commit — checkable years
later by anyone, including someone who was not there. The author also states the
completion at the moment they complete it, rather than an agent inferring it
afterwards from a diff.

Rules that make it safe to run over the whole history on every invocation:

- **Idempotent.** A completion already recorded — `status: done` *and* the id cited
  in `92_audit/` — is skipped. No state is kept about where the last run stopped,
  because state that can be wrong is worse than a scan that costs a second.
- **First commit per id wins.** A later commit naming the same id is a follow-up
  fix, not a second completion.
- **A trailer naming an id no Backlog item has is reported, never invented.** The
  script does not create documents.

Writing the status and audit line by hand stays entirely valid. The trailer is the
cheaper path, not a required one.

## 7. Validator contract (`scripts/docs_validate.sh`)

Deterministic, read-only, no LLM, no network. Usage:
`docs_validate.sh [--strict] [docs_dir]` (default `./docs`).

### Names fail, links warn

Since 0.28.0 the validator has two severities, and the line between them is not
importance — it is **what a wrong one costs to notice**.

- **A wrong name silently merges two different things.** A duplicate `id:` makes
  every reference to it ambiguous, and neither reference looks wrong. An id whose
  prefix does not match its folder breaks the convention the folder is read by.
  Nothing downstream can recover from these, so they **FAIL**.
- **A wrong link is one broken edge.** It is visible the moment anyone follows it
  and harmless until then, and the document it sits in is still perfectly readable.
  These **print as `NOTE` and pass**.

`--strict` turns every soft finding back into a `FAIL`. That is the mode for CI;
the default is the mode for working.

**Why the default moved.** Two measurements on real repos, and they say different
things. Every failure the old validator produced across both — 7 of 7 — was a false
positive from the one check that could not tell a re-mention from a conflict; that
check is fixed above, not demoted. Separately, the same repo's `23_backlog/` is empty,
and its README states the reason: a Backlog item's `source_ref` must resolve to a
Decision or an Issue, most of its workstreams have neither, so the work was written
into the roadmap instead. A rule people route around enforces nothing, while a rule
that prints without blocking is still read.

### Hard checks — these fail

| Tag | Check |
|---|---|
| `[ref]` | A duplicate `id:`. A component name declared in two architecture docs **with conflicting backticked paths** — two different paths under one name are genuinely ambiguous, since edges and cards resolve components by name. Repeating a name with no path of its own is a *re-mention*, which a cross-cutting flows document has to do, and is not reported. |
| `[frontmatter]` | A missing `id:`; an `id:` prefix that does not match its folder; an empty or invalid `lane`/`status`/`outcome` enum. |
| `[audit-append]` | `92_audit/` files are append-only vs git HEAD (no deleted or rewritten lines). Skipped when git or HEAD is unavailable. |
| `[profile]` | Every token in `.docs-kit.json`'s `owns` is one the standard defines (§9.1). A value outside the enum is a typo, and a typo there silently drops a folder from the scaffold. |

### Soft checks — these print, pass, and fail only under `--strict`

| Tag | Check |
|---|---|
| `[ref]` | A `*_ref:` that is empty or resolves to no `id:` under docs/. An `04_api/` `service:` naming no declared component. |
| `[backlog]` | A Backlog item with no `source_ref:`. |
| `[frontmatter]` | A required field other than `id` missing (§4); a Proposal with no "Alternatives considered" heading. |
| `[amended-by]` | An `amended_by` or `rejected` entry citing a `DECISION-NNN` that resolves to nothing. |
| `[anchor]` | A path a layer 1 document names that no longer exists: a `components` entry's backticked `path/in/repo`, a figure fence's `code:` header, an `04_api/` `generated_from` artifact. |

Informational lines, which never affect the exit code in either mode:

| Tag | Meaning |
|---|---|
| `NOTE [layout]` | A folder this repo's profile calls for is missing (§9.1). A folder *outside* the profile is never reported. |
| `NOTE [profile]` | `.docs-kit.json` declares `owns`, and the repo shows a surface it does not account for — see §9.2. |
| `NOTE [stale]` | A layer 1 document carries `verified_at: <rev>` and some of the paths it names have changed since that rev — or the rev is not a commit in this repo. |

Output: one line per finding — `FAIL [tag] <file>: <message>` or
`NOTE [tag] <file>: <message>` — then a summary. A run with notes and no failures
says so and gives their count, rather than reporting that everything passed.
Exit codes: `0` clean, `1` violations found, `2` setup error (e.g. docs/ missing).

`_archive/` subfolders are validated exactly like the folder above them (§2).

### Why `[anchor]` fails and `[stale]` only warns

Every load-bearing fact in layer 1 already carries an anchor into the source: a
component names its `path/in/repo`, every figure fence takes a `code:` header. Until
these checks existed, nothing used them.

- **A path that no longer exists is not a matter of opinion.** The document cannot be
  verified against anything, so it is reported every run — as a `NOTE` by default and
  a `FAIL` under `--strict`, because a moved path is a broken link, not a wrong name.
- **A path that merely changed is not proof the document is wrong.** So `verified_at`
  produces a `NOTE`, on the same reasoning as §8's warn-only hooks: blocking on a
  false positive teaches people to switch the check off.

The comparison is `git diff --name-only <verified_at>` against the **working tree**,
not against HEAD. `docs-sync` runs at the end of a session, before the work is
committed; comparing against HEAD would hide exactly the changes that session made.

#### What counts as one anchor

An anchor is a **path expression**, not necessarily a single filename. Two forms are
legal wherever a path is named, and both were already being written before anything
accepted them:

- **A comma-separated list**, in a `code:` header only: `code: app/page.tsx, lib/auth.ts`.
  A scenario rarely lives in one file, and the alternative — one fence per file — would
  split a flow that is genuinely one flow. Each item is checked separately. A
  `components` entry stays exactly one path, because a component is one thing.
- **A glob**, in either form: `lib/validators/*.schema.ts` resolves if it matches at
  least one file. Fourteen sibling schemas are one fact about the codebase, not
  fourteen facts, and listing them all is a list that goes stale on the next file added.

`*` and `?` are the only metacharacters. `[` is **not** one: `app/users/[id]/page.tsx`
is a real Next.js directory, and treating its name as a bracket expression would report
a file that is sitting right there as missing. Existence is tested literally first, so
any path that exists as written is settled before globbing is considered.

Against `git diff` a glob is compared by its longest literal directory prefix, since no
pattern will ever equal a filename git prints. That is coarser than the glob, and
deliberately so: a `NOTE [stale]` that fires slightly too often costs one re-read, while
one that never fires costs the whole check.

Values containing `<` or `>` are treated as template placeholders and skipped — that
is what lets a fresh scaffold pass clean.

**This is the mechanism by which docs are synchronised to a specific version**, and it
costs no tokens: it is a filesystem test and a `git diff`. It also bounds the expensive
half of the work — an LLM re-reading code to check a document only has to look at the
documents this check flagged.

The validator checks **form, not content**. It is the source of truth for form:
skills never "eyeball-validate" in its place. `[anchor]` does not change that — it
verifies that a named path exists, never that the sentence about it is still true.

## 8. Enforcement hooks (warn-only, deterministic)

Two docs-model hooks, both plain scripts, **no LLM calls**:

1. **PostToolUse** on `Edit|Write`: if the edited path is under
   `docs/02_architecture/`, `docs/03_business-logic/` or `docs/04_api/` → warn
   (user + agent):
   "this is layer 1, amended only via the Decision workflow — confirm a Decision
   ref exists." Paths under `templates/docs/` are exempt: the plugin ships its own
   template tree at exactly that shape, and firing on it would train docs-kit's
   own maintainers to switch the hook off.
2. **Stop**: scan the session transcript for edited files, look each one up in
   `docs/MAP.tsv` (§10), and report **by document, not by file**:
   - a document whose claimed paths this session edited and whose `verified_at`
     the code has moved past → *changed since last verified*;
   - the same, but the document has no `verified_at` at all → *never verified*,
     which is a weaker and different claim, so it is worded differently;
   - a file nothing claims, sitting in a directory where other files *are* claimed
     by name → *added beside something documented*.

   A document the session also edited is never reported: it was already being kept
   current, and saying so would be describing the user's own work back to them.

**Why it asks about documents and not about path shapes.** Until 0.25.0 this hook
matched `sensitive_paths` globs against every edit. Measured on a real monorepo whose
service directory is named `apps/api/`, `**/api/**` matched **57 of 57** edited files
— every test, every changelog — because *a directory called api* and *an API
boundary* are not the same thing and no pattern can tell them apart. It fired in 15
of 36 sessions and could not be silenced: the engagement check looked for
`docs/22_decisions/` in a repo that used `docs/20_decisions/`. A path a document
claims is a fact the repo states; a path that looks sensitive is a guess.

**Why warn-only:** these rules have not been battle-tested across real projects
yet. Blocking on a false positive teaches users to disable the hook entirely,
which loses all enforcement. Warn now; promote to block only after the trigger
rules have been tuned in practice.

**Hooks are silent unless the repo declares itself a docs-kit repo** — a
`.docs-kit.json` at the root, or a `docs/22_decisions/` folder. A bare
`docs/README.md` is not a declaration; every documented project has one, and
accepting it is what made the Stop hook fire in a repo using a different folder
scheme entirely.

### The Stop hook is the only thing that may ask for a sync

**A session that changed code does not owe anyone a `docs-sync`.** The obligation
exists only when some document claims a file the session touched, which is precisely
what the Stop hook computes from `MAP.tsv` (§10) — and the answer is usually no. Of
310 recorded sessions, **35** ran in a repo where the hook may fire at all (three
repos), and it fired in **1** of those.

Read the denominator carefully, because the first attempt at this number was wrong.
Grepping every transcript for the hook's message returns 5, and 4 of those are the
docs-kit repo itself, where the string appears in the output of tests that exercise
the hook rather than in a real fire. The eligible set is what counts: sessions whose
recorded `cwd` holds a `docs/` and either `.docs-kit.json` or `docs/22_decisions/`.

So no rule anywhere may say "end every session with `docs-sync`". The `CLAUDE.md`
block docs-init writes carries the sharp end of this, because it loads in every
session of every repo and therefore outranks any hook: until 0.30.0 it said exactly
that, which fired on every one of those 35 sessions while the mechanism built to
answer the same question fired on one. A sync is owed when the hook names a document, or right after
a Decision is approved. Nowhere else.

**Finishing a Backlog item is not a sync trigger either.** `Closes: BACKLOG-NNN` in
the commit message is the author saying it, and `docs_close.sh --apply` writes the
status and the audit line from that (§6.1). Asking a person to also flip a field by
hand is asking them to restate what they already stated.

The crew layer (0.26.0) adds two PreToolUse hooks — an explain-gate on
AskUserQuestion and a resource-guard on Bash — under this same doctrine:
deterministic, warn-only by default, and silent unless `.docs-kit.json`
carries a `crew` key. Their evidence rules, their per-repo promote-to-block
flag, and their declared limits live in `EXECUTION.md` §8.

## 9. Configuration — `.docs-kit.json` (optional, in the target repo root)

```json
{
  "owns": ["data", "endpoints", "screens", "jobs"]
}
```

Its presence is also what tells the hooks this repo uses docs-kit (§8), so a repo
with no conditional surface still benefits from writing `"owns": []`.

**`sensitive_paths` is no longer read (0.25.0).** It configured the Stop hook's glob
matching, and the glob is gone: the hook now asks `docs/MAP.tsv` which document
claims an edited file. The key is ignored rather than rejected — an old config stays
valid, it just no longer changes anything. Nothing replaces it, because the thing it
was tuning is now derived from the documents instead of declared beside them.

### 9.1 `owns` — what this repo holds title to

`owns` declares what this repo holds title to — `data` (tables), `endpoints` (a
contract it publishes), `screens` (routes), `jobs` (consumers, schedules),
`deploys` (something that gets shipped and operated). **It is optional; a repo
that omits it gets all 17 folders and behaves exactly as it did before profiles
existed.**

It is also what decides the shape of `docs/`:

| `owns` token | folders it justifies |
|---|---|
| `endpoints` | `04_api/` |
| `screens` | `60_fe-integration/` |
| `deploys` | `40_services/` · `50_runbooks/` · `70_deploy/` |
| `data` | — |
| `jobs` | — |

The other twelve folders are **core**: every repo gets them, because the questions
they answer — what are we building, what is it made of, how does it change, what
happened, and what the kit itself got wrong here — have no profile in which they
stop applying.

`data` and `jobs` open no folder on purpose. A repo's tables live in the ```` ```erd ````
block inside `02_architecture/`, and its workers are `[queue]` components in the same
place; both are core. The two tokens still earn their keep as evidence below, and as
the answer to "what is this repo" for anyone who asks.

The map lives in exactly one file, `scripts/docs_profile.sh`, which both the
scaffold and the validator source. Which folders belong here is one fact, and the
kit does not get to hold it in two places.

**Three rules keep a profile from becoming state that rots:**

1. **No declaration means no branching.** Absent `owns` → all 17, exactly as before.
   Nothing a previous version scaffolded changes shape until somebody declares
   something. `"owns": []` *is* a declaration — a library that owns nothing
   conditional — and is not the same as saying nothing.
2. **A folder outside the profile is never a finding.** `--sync` adds and never
   removes; `NOTE [layout]` reports only folders the profile calls for and that are
   missing. A repo that declares `owns` after the fact keeps every folder it already
   had. Deleting documentation because a config line changed is not a trade anyone
   agreed to.
3. **A token outside the enum is `FAIL [profile]`, not a shrug.** `owns` is closed —
   `data` · `endpoints` · `screens` · `jobs` · `deploys` — and now that it decides
   folders, `"endpoint"` for `"endpoints"` silently costs a repo its `04_api/`. That
   is a typo with consequences, so it fails.

### 9.2 Keeping `owns` honest

A project changes: a backend grows a frontend, a service stops owning its tables.
So `owns` is a declared fact and gets the same treatment as `verified_at` and
`generated_from` — declare it, and let something deterministic notice when reality
disagrees. The validator emits `NOTE [profile]` on two kinds of evidence, neither needing any
knowledge of a framework:

- **a component's `[kind]` tag** — `[db]` implies `data`, `[ui]` implies `screens`,
  `[queue]` implies `jobs`. This is the stronger signal: it is the repo saying in its
  own architecture doc what it holds, with a path to prove it.
- **a folder holding real documents** — `04_api/` with contracts implies `endpoints`;
  anything in `40_services/`, `50_runbooks/` or `70_deploy/` implies `deploys`.

A file byte-identical to its shipped template is a **seed** and counts as neither, or
a fresh scaffold would trip the check on day one.

Only the *growth* direction is checked. `owns` claiming something the repo no longer
has cannot be told apart from "nobody has written it yet", and guessing there would
cry wolf.

**Changing `owns` is a layer 1 change** — what a repo owns is architecture — so it
goes through the Decision workflow like any other amendment. Adding the folders a new
`owns` justifies is `/docs-kit:docs-upgrade`, which adds and never overwrites.

### 9.3 Where a profile comes from

`scripts/docs_detect.py` proposes one. It reads manifests, compose files and
deployment artifacts and prints `owns-hint:` lines, each carrying the evidence that
produced it on the same line — `owns-hint: endpoints — go.mod declares
github.com/gin-gonic/gin`. It writes nothing.

**A hint is never a declaration.** `docs-init` shows the hints, asks with
AskUserQuestion, and scaffolds the answer — not the guess. That asymmetry is what
makes generous hinting safe: an unconfirmed hint costs one extra option in a dialog
the user is answering anyway, while a silent one would put a wrong fact in a config
file that decides the shape of the tree.

### 9.4 `crew` — turning on the execution layer

```json
{ "crew": { "enforce": false } }
```

The presence of a `crew` object turns the execution layer on for this repo:
the two crew hooks start reading, `scripts/crew` starts working, and
`/docs-kit:crew-init` is what writes it. An absent key is the layer switched
off — nothing fires, nothing changes shape, the same guarantee `owns` gives
(rule 1 above). Field reference and defaults live in `EXECUTION.md` §9; the
one field worth naming here is `enforce`, which promotes the explain-gate from
warn to deny for this repo only, and stays `false` until the shipped test has
proven the gate red-for-the-right-reason and the log shows warnings being
ignored.

## 10. Generated HTML views (read models)

`scripts/docs_render.sh` (→ `docs_render.py`, Python 3.9 stdlib, no LLM, no
network) generates three self-contained pages into `docs/`, styled per
`design/design-system.html` ("change-control print"):

| Page | Content |
|---|---|
| `docs/index.html` | Menu beside README.md: system map (clickable), sheet cards, Layer-3/Oversight listing, the one hard rule |
| `docs/current.html` | Layer 1: product cards, roadmap board, component cards, data-flow figure, API contract tables, constraints, revision block, business-flow sequences |
| `docs/changes.html` | Layer 2: issue/backlog boards, proposal & decision tables, trace chains, audit table |
| `docs/INDEX.md` | **The read model for agents**, as the three pages are the read model for people: one line per document — id, status, refs, file, description |
| `docs/MAP.tsv` | **The reverse index**: one line per path a layer 1 document claims — `path`, `doc`, `claim`, `verified_at` |

And two read-only gates, neither of which writes anything:

| Command | Asks |
|---|---|
| `docs_render.sh --check .` | are `INDEX.md` and `MAP.tsv` current with the markdown? |
| `docs_render.sh --check-api .` | do the API contracts match their generated artifacts? |

### `INDEX.md` — the rule that makes it worth generating

**A skill reads `INDEX.md` and then opens only the ids it needs. It never globs a
layer 2 folder.** Reading every Decision to find out what is settled costs one whole
file per document and grows forever; reading the index costs one line per document
and produces the same answer. The header is a fixed cost, so the saving is small at
five documents and large at five hundred — which is the point, since the problem only
appears at the second number.

Archived documents appear in the index with an `_archive/` prefix on their file
column, so nothing disappears and the agent still knows where to look.

**A stale index is worse than a missing one, because the agent trusts it.** That
makes it the one generated file needing a gate, and the renderer provides it:

```bash
docs_render.sh --check .     # 0 = current · 1 = missing or stale · 2 = no docs/
```

It writes nothing and rebuilds the index through the same code path a real render
uses, so it cannot disagree with one. Only the two text read models are checkable
this way — the HTML pages embed a generated-at stamp and a git ref, so they differ
every run by design. Repos that keep docs in review should run it in CI beside the
validator; `/docs-kit:docs-check` runs it too.

### `MAP.tsv` — the same relation, read the other way

`INDEX.md` answers *what documents exist*. `MAP.tsv` answers the question nothing
could ask before it: **which document describes this file**.

Nothing new is authored for it. The relation was always stated in the markdown —
every component names its `path/in/repo`, every figure fence takes a `code:` header
— but it existed only inside a validator run and vanished when the process exited.
A hook firing on an edit therefore had no way to consult it, and guessed from path
shape instead, which is not the same question and does not have the same answer.

```
path                          doc                              claim                    verified_at
lib/comment.ts                02_architecture/architecture.md  component:comment-composer  a1b2c3d
lib/validators/*.schema.ts    02_architecture/architecture.md  erd:1                       a1b2c3d
```

**It carries no staleness verdict, on purpose.** Whether a claim has gone out of
date is a git question whose answer changes with every commit, while this file
changes only when the markdown does; baking the verdict in would make it wrong
within a minute of being written. `verified_at` is carried instead, and a reader
joins it against `git diff --name-only` itself — which is what the Stop hook (§8)
and `docs-sync` step 5 both do.

A stale `MAP.tsv` fails in the more dangerous direction than a stale `INDEX.md`: it
makes the hook **quieter** rather than wrong, and silence is the failure nobody
notices. That is why `--check` gates both.

Rules:

- **Read model only.** The renderer never edits markdown; the markdown stays
  the source of truth. Generated pages carry a `GENERATED` header comment —
  `INDEX.md` included — never hand-edit them; regenerate with
  `/docs-kit:docs-render` (docs-init creates them, docs-sync refreshes them).
  A derived read model is also why the store stays markdown in git: the index can
  be regenerated in any shape a query needs, while git keeps the diff, the blame,
  and the ability to commit a doc change in the same commit as the code change.
- **Deterministic.** Same input docs → same output bytes; only the
  generated-at stamp moves (override with `DOCS_KIT_NOW=<ISO>` for
  reproducible output). Files sorted by name; logs newest-first.
- **Data-flow syntax** (one edge per line in `data_flow`):
  `a -> b` sync · `a ~> b` async (teal, dashed) · `a -> b : label` edge label.
  Component entries may annotate a kind — `postgres [db]`, `jobs [queue]`,
  `dashboard [ui]` — which sets the node icon/tint; unannotated entries are
  services; nodes absent from `components` are drawn dashed as external.
- **Figure standard — a figure is never shrunk to fit.** Text that has been
  scaled down to make a diagram fit is a diagram nobody reads. Every figure is
  drawn at its natural size; one wider than the column scrolls inside its own
  frame.

  `data_flow` has exactly one style: a **graph** — longest-path layering,
  alphabetical within a column, every edge label placed in the gap after its
  source column, a gap widened to hold it so a label can never land on a node.
  It stays a graph at every density. The complete edge table is printed beneath
  it, always: the figure carries the shape, the table carries the words, and the
  table is also the figure's accessible reading. Unparseable input falls back to
  its own source text — never a guessed diagram.

  **A cycle is not a degradation.** `a -> b` and `b -> a` together mean
  request/response, a callback, a cache read-back, or a retry — ordinary shapes
  in a running system, not a drawing problem. Before layering, the renderer
  lifts out a *feedback arc set* (DFS from each root in name order; an edge into
  a node still on the stack is a back-edge) and layers what remains. The lifted
  edges are then drawn back in on **return lanes below the rows**, widest span
  in the deepest lane so shorter returns nest inside rather than cross. A
  back-edge is told apart by its route alone — nothing else is drawn under the
  rows — which spends no new hue and keeps it distinct from the teal dashed
  async edges it may itself be one of. A self-edge (`a -> a`) is a loop in its
  own lane. The figure caption states how many back-edges it holds.

  The feedback arc set is not minimal — that is NP-hard — but it is **stable**:
  every iteration order in its computation is sorted, so the same input always
  lifts the same edges, which is what keeps the rendered bytes reproducible.

  The density budget therefore no longer selects a presentation. It decides when
  to **warn**:

  | limit | value |
  |---|---|
  | nodes | 20 |
  | edges | 32 |
  | nodes stacked in one column | 10 |
  | participants in a sequence | 8 |
  | steps in a sequence | 16 |
  | states in a state machine | 12 |
  | transitions in a state machine | 24 |
  | tables in an ERD | 10 |
  | columns in one table | 15 |
  | types in a class diagram | 12 |
  | members in one type | 15 |

  Past any of these the flow is still drawn as a graph, at natural size,
  scrolling inside its own frame; a note suggests splitting it across
  Architecture docs rather than compressing the picture. A sequence over budget
  degrades to its numbered step table.
- **Business logic** (```` ```flowchart ```` fenced block in the *body* of a
  `03_business-logic/` doc — or of a product or architecture doc) renders as a
  flowchart. It answers the one question a sequence cannot: *what happens when
  condition Y holds*. Grammar, deliberately the same family as `data_flow` and
  ```` ```flow ```` rather than a third dialect:

  | line | meaning |
  |---|---|
  | `title:` `trigger:` `outcome:` `code:` | optional headers, exactly as in ```` ```flow ```` |
  | `decide: <node> — <question>` | declares `<node>` a branch point; drawn as a diamond |
  | `a -> b` · `a ~> b` | a step · an async step |
  | `a -> b : label` | edge label — **on an edge out of a decide node the label IS the branch name** |
  | `start` · `end` | reserved names, drawn as stadium terminals |

  There is no branch syntax and no nesting. A branch is an ordinary labelled
  edge, which means the layered engine places it in the gap after its source
  column by the same rule as every other label, and a loop (`validate -> input :
  sai định dạng`) is an ordinary back-edge on a return lane. Both come free from
  the data-flow engine; a flowchart is the same layering problem with different
  boxes, and giving it its own engine would mean maintaining that routing twice.
  A branch label takes the diamond's own hue — no new hue is spent, it is the
  same L1 — because it is the most load-bearing text on the figure.

  Its budget, warn-only on the same principle as the graph's: **20 nodes ·
  28 edges · 8 decide nodes**. The numbered step table, and the decide-question
  table when there is one, print under every chart rather than as a rescue.

  Rules that read better as a table than as a picture stay markdown tables — a
  decision table needs no grammar of its own.
- **State machines** (```` ```state ```` fenced block, read from the same three
  doc kinds as ```` ```flowchart ````) render as an entity lifecycle. A flowchart
  answers *which way does this branch go*; a state machine answers *where can this
  thing be, and what moves it*:

  | line | meaning |
  |---|---|
  | `title:` `entity:` `code:` | optional headers; `entity:` names what carries the lifecycle |
  | `initial: <state>` | the one start state — drawn with a blue (L1) 2px stroke |
  | `final: a, b, c` | the end states — drawn with a second border **inside** the box |
  | `state: <name> — <meaning>` | optional declaration; declaring one opts the file into a warning listing the rest |
  | `a -> b : event` · `a ~> b : event` | a transition · a transition made by a background actor |

  `initial:` and `final:` mark **real states** rather than adding `start` / `end`
  pseudo-nodes: a six-state machine has to show six boxes, and an `end` sink would
  need a fabricated edge out of every terminal state, inflating the figure and the
  transition table alike. The start state is marked by its stroke and not by a dot
  beside the box, because that dot would sit in the label gap where edge chips are
  placed; the final border is drawn inward and not as an outer ring, because column
  widths come from the node width and a ring would push a box into its neighbour.

  There is no guard syntax. A condition worth drawing deserves a
  ```` ```flowchart ```` beside it, which is exactly what the section above is for.
  A lifecycle loops by nature — a retry, a return to the warehouse, a refund after
  delivery — and every one of those is an ordinary back-edge on a return lane,
  inherited from the graph engine rather than reimplemented.

  Budget, warn-only as everywhere else: **12 states · 24 transitions**. The
  transition table prints under every machine, and the state-meaning table too when
  any `state:` line carried a meaning.
- **Data model** (```` ```erd ```` fenced block in the *body* of an
  `02_architecture/` doc, and only there — a data model filed under a product or
  a business rule is misfiled, and rendering it anyway would hide that; one fence
  per document, holding the tables **that document's service owns**) renders as
  an entity-relationship diagram, in the **Data model** sub-section of §3 right
  after Components:

  | line | meaning |
  |---|---|
  | `title:` `code:` | optional headers |
  | `table: <name>` | opens an entity; every following line is one of its columns |
  | `<name> <type> <flags…>` | one column, flags in any order |
  | flag `pk` | primary key |
  | flag `fk -> <table>.<column>` | foreign key — **this is what draws a relationship** |
  | flag `unique` | on an `fk`, makes the relationship 1:1 |
  | flag `null` | nullable — the relationship is optional |
  | trailing ` — <gloss>` | optional explanation, the same separator `decide:` and `state:` use |

  **There is no relationship syntax, and cardinality is never written by hand.** A
  foreign key *is* the relationship, and what it means is not a matter of opinion:
  many child rows point at one parent row. So the child end takes a crow's foot,
  the parent end a single bar, `unique` turns the child end into a bar as well, and
  `null` adds the empty ring for zero-or-one. Writing those by hand would create a
  second source for one fact, and the picture would eventually disagree with the
  column list printed beneath it.

  Entity boxes are the first nodes in the engine whose height is not fixed — an
  entity is as tall as its table is long. That is a change to the shared layout,
  not a second layout: columns measure summed heights instead of multiplying by a
  row pitch, and everything else — layering, label gaps, return lanes — is
  untouched. A self-referencing FK is an ordinary back-edge on an ordinary return
  lane. `pk` and `fk` tags stay graphite: they name no layer, so they buy no hue.

  Budget, warn-only: **10 tables · 15 columns in one table**. The column table —
  table · column · type · keys · relationship · note — prints under every ERD, and
  a schema with no foreign key at all prints only that table, because a picture of
  unconnected boxes says nothing the table does not.

  A collapsed **DBML** block prints last, for pasting into dbdiagram.io when a
  drag-and-drop view is wanted. It is a third rendering of the same parse, beside
  the figure and the column table — not a second source: it reads the parsed
  tables, never the fence text, so it cannot describe a schema the other two do
  not. Cardinality is still never written by hand (`>` from the foreign key, `-`
  when the key is `unique`). **Nothing writes it to a file, and a `.dbml` in the
  repo would be the mistake it exists to avoid** — a second thing to edit, frozen
  the moment it is written. There is deliberately no reverse path: reading DBML
  back in would create a second place to author the schema.
- **Types** (```` ```class ```` fenced block in the *body* of an
  `02_architecture/` doc, and only there) renders as a class diagram, in the
  **Types & contracts** sub-section of §3 right after Data model. Data model is
  the data as stored; this is the code's own contracts:

  | line | meaning |
  |---|---|
  | `title:` `code:` | optional headers |
  | `class: <name>` · `interface: <name>` | opens a type; an interface is drawn with an `«interface»` stereotype |
  | `extends <name>` | a relation line inside the block — solid edge, hollow triangle at the parent |
  | `implements <name>` | a relation line inside the block — **statically** dashed edge, hollow triangle at the interface |
  | `+ <name> <type>` · `- <name> <type>` | a public · private member |
  | a member containing `(` | a method — lower compartment, split at the paren rather than at whitespace |
  | trailing ` — <gloss>` | optional explanation, the shared separator |

  **Association is derived, never written.** A field whose type names another
  declared type draws a plain edge, for the same reason `fk` draws an ERD
  relationship: one source per fact. `*`, `[]`, `...` and a `map[…]` wrapper are
  stripped first, so `*http.Client` matches nothing — a type from another package
  is not in this picture. Method signatures are **not** scanned; a signature
  naming every type in the package would draw a graph nobody can read.

  Composition and aggregation are deliberately absent: the boundary between them
  generates more argument than insight, and being hand-written it drifts from the
  code. The `implements` dash is **static** — marching dashes already mean async
  or fast-lane, and a realization arrow is neither. Visibility glyphs and the
  stereotype stay graphite: they name no layer, so they buy no hue.

  A class box is the ERD's entity box with a stereotype in its header band and a
  hairline between the two compartments — not a second kind of node, and neither
  addition changes any height.

  Budget, warn-only: **12 types · 15 members in one type**. The member table —
  type · member · kind · visibility · signature · note — prints under every class
  diagram.
- **API contracts** (```` ```api ```` fenced block in the *body* of an `04_api/`
  doc) render in §4 of `current.html` as a **table, not a figure** — and that is
  the design, not a shortcut. Every other fence draws because it carries a shape:
  a sequence, a lifecycle, a set of relations. A list of operations has none.
  Drawing it would spend a figure number to put boxes around a table, when §10's
  own rule is that the table is what carries the words.

  | line | meaning |
  |---|---|
  | `title:` `base:` `code:` | optional headers |
  | `<VERB> <path>` | one operation; `VERB` is uppercase — `GET`, `POST`, `RPC`, `QUERY` |
  | `event <name>` | an event this service publishes |
  | `<- <Type>` | what it accepts |
  | `-> <Type>` | what it returns |
  | trailing ` — <gloss>` | explanation, the shared separator |

  There is no status-code syntax, no field list, and no schema — see §4. Anything
  the grammar does not recognise makes the whole block fall back to its source
  text, because a contract nobody can parse must never be shown as one somebody can.

- **Business flows** (```` ```flow ```` fenced block in the *body* of any
  `01_products/`, `02_architecture/` or `03_business-logic/` doc) render as a
  sequence figure —
  lifelines left to right, time down the page, participants ordered by first
  appearance. Steps use the same edge grammar as `data_flow`; `a -> a` is a
  self-call. Optional `title:`, `trigger:`, `outcome:`, `code:` header lines
  frame the scenario. They are collected into one **Business flows** section on
  `current.html` rather than left inside each card, and a participant naming a
  component picks up that component's icon and kind. This is deliberately a body
  fence and not frontmatter: the validator parses frontmatter with awk, and the
  flows belong next to the prose that explains them.
- **Component entries carry their anchor in the source.** Full grammar:
  `name [kind] `path/in/repo` — what it does`. The description says what the
  component *is*, in one sentence, written after reading the code; the backticked
  path says where to go read it. Everything a card shows beyond that —
  role, upstream, downstream — is derived from `data_flow`, never authored twice.
  A `### <name>` section in the architecture body becomes that card's expandable
  detail.
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
  animations; `prefers-reduced-motion` disables all of it. The green LED means the
  validator printed **nothing at all**: a run with notes but no failures gets a static
  graphite dot and the count, because a generated page that reads *clean* over a dozen
  refs resolving to nothing is worse than one that says nothing (§7).
- The validator ignores `docs/*.html` (it only reads `.md`); check 4's
  append-only rule is unaffected. `docs/INDEX.md` *is* scanned — it carries no
  frontmatter, so it defines no id and holds no ref, and it is inert to every
  check. It does count toward the file total the validator prints.

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
- **`name:` is a proper noun, not prose — it is not translated in either
  direction.** A Vietnamese-speaking team whose product is called *Đối soát giao
  dịch* keeps that name; one whose product is called *Reconciliation* keeps that
  one. The field is a nav target and a thing people say out loud, which puts it
  with the domain terms above, not with `problem:` and `users:`.
- **Names within one set stay in one register.** If `01_products/` already holds
  `OrderHub API` and `Merchant Dashboard`, the next product is named the same
  way. The generated sidebar lists them as siblings under §1, so a lone
  odd-register name reads there as a leak rather than as a choice — whichever
  register is already established is the one that is right. Nothing enforces
  this; it is a review question, not a validator check.
- **A title may be Vietnamese; the file name may not.** Whatever `name:` says,
  the file it lives in stays ASCII — `reconciliation.md`. File names are keys,
  not prose: they appear in shell commands, git output, and URLs, and §3 already
  makes them non-referential, so there is nothing to gain by translating them.
- **Anchor slugs fold diacritics anyway** (`slugify()`), and dedupe within a
  page. Nothing enforces the rule above, and the failure it prevents is quiet:
  a plain `[^a-z0-9]` filter would collapse both `phân-quyền` and `phần-quyền`
  to one HTML id, so the sidebar link would open the wrong document.
- `<html lang="vi">`, since the prose dominates the page.

## 12. Feedback on the kit itself — `99_feedback/`

Everything else under `docs/` describes the product. This folder describes **the
kit**, and it exists because the previous arrangement had no place to put a
problem: an agent that hit a wrong `FAIL`, a hook that stayed quiet, or a rule
that could not be followed said so once in a chat session, and the session ended.
The report reached nobody, and the next repo hit the same thing.

**One problem, one file, and the file is the prompt.** No summary step, no
rewriting into a bug tracker's fields — `docs_feedback.sh show <id>` prints
something that can be pasted into a docs-kit session as it stands. That is the
whole delivery mechanism, and it is deliberately the cheapest one available:
a report that costs a paragraph of re-explaining is a report that does not get
sent.

### 12.1 What qualifies

| Case | Example |
|---|---|
| A script or hook contradicts the standard | validator `FAIL`s something §4 permits; a hook silent where §8 says it warns |
| Finishing an ordinary task needed a workaround | hand-editing a generated file, skipping a gate, running an undocumented step |
| A document states something this repo proved untrue | `STANDARD.md`, `EXECUTION.md`, or a `SKILL.md` describing behaviour that does not happen |
| A real fact has no field to live in | the model covers nothing that fits, so it was recorded nowhere |

The second row is the highest-signal one. A workaround is a cost already paid,
which is different in kind from a cost imagined — it needs no argument about
whether the friction is real.

### 12.2 What does not

- **Your own mistake, correctly caught.** A rejected bad ref is the validator
  working.
- **A problem with *this* repo** — its code, its content, its conventions. That
  is an Issue in `20_issues/`.
- **A preference with no named cost.** "I would call it something else" is not
  a report.
- **A problem already filed.** Append one line to that file's *Seen again*
  section. Recurrence is evidence; a second file is noise.

One test before writing anything: **if you cannot say what the kit should do
differently, it is not ready to file.** Say it to the user instead.

### 12.3 Why the folder is core, and why it stays

Core, in every profile, for the same reason `92_audit/` is: a repo with nowhere
to record the problem records nothing, and "we will remember to mention it"
is exactly the mechanism that has already failed.

A report stays after it is fixed, with `status: fixed` and `fixed_in:` naming the
version. It then answers the question a future reader actually asks — *why did
this repo do that strange thing for a while* — and one line of history is far
cheaper than the investigation it replaces.

### 12.4 The script (`scripts/docs_feedback.sh`)

Deterministic, read-only except for the one file it writes.

```bash
docs_feedback.sh new  <slug>   # next id + the template + the context, filled in
docs_feedback.sh list          # id · status · severity · about · title
docs_feedback.sh show <id>     # the report verbatim — this is "send it"
```

`new` stamps the kit version, this repo's profile, the git rev, whether crew is
stamped, and the platform. **These are the fields a writer gets wrong**, and a
problem that will not reproduce is nothing but its context — which is the same
reason §6.1 prefers a commit trailer to a session's recollection.

The template is `docs/99_feedback/TEMPLATE.md` in the repo when present, and the
kit's copy otherwise, so a team may adapt the form without losing the command.

Exit: `0` done · `2` setup error · `3` no `99_feedback/` — the repo predates the
folder, so `/docs-kit:docs-upgrade` adds it.
