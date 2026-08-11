# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions live in `.claude-plugin/plugin.json` (the single source of truth
for the plugin version — the renderer stamps it into every generated page).

## [0.23.0] — 2026-08-11

### Added — item F: the docs tree follows what the repo actually owns

`docs/` has been 16 folders for every repo since the beginning. A library got a
`70_deploy/`; a backend got a `60_fe-integration/`. That invariant is gone, and this
entry is mostly about the four ways it could have gone wrong instead.

**One axis, not two.** The proposal called for `scope` (system/service/app/library)
beside `owns`. After item D landed — architecture already splits per service by
globbing the folder — `scope`'s only remaining job was "is this thing deployed?",
which is one token, not an enum. So `owns` gained a fifth token, `deploys`, and
`scope` was dropped before it existed. One declared field, one less thing to drift.

| `owns` token | folders it justifies |
|---|---|
| `endpoints` | `04_api/` |
| `screens` | `60_fe-integration/` |
| `deploys` | `40_services/` `50_runbooks/` `70_deploy/` |
| `data`, `jobs` | none — an ERD and a `[queue]` component both live in core folders |

The other eleven folders are core. A library scaffolds 11; a fullstack service still
scaffolds 16.

**The map lives in one file.** `scripts/docs_profile.sh` is sourced by both the
scaffold and the validator. "Which folders belong here" is one fact, and the kit does
not get to hold it in two places — the validator's own `owns` reader was deleted and
now calls the shared one.

### The four ways this could have gone wrong, and what stops each

1. **Every repo scaffolded by an older docs-kit changes shape.** It does not. An
   absent `owns` key means "nobody declared" and yields all 16, exactly as before.
   Nothing branches until somebody declares something. `"owns": []` is a different
   statement — a library that owns nothing conditional — and the reader distinguishes
   the two, which the 0.22.0 reader could not.
2. **A missing folder becomes ambiguous.** It is answerable: `.docs-kit.json` says.
   And because `owns` now decides folders, a typo in it costs a folder silently — so
   an unrecognised token is `FAIL [profile]` at both ends, refused by the scaffold
   before it writes anything and failed by the validator on a repo where it got in.
3. **`--sync` loses its definition.** It syncs toward the profile and still only
   adds. Declaring a new token and re-syncing is the whole upgrade path when a repo
   grows an API. The other direction does nothing: removing a token removes no
   folder and no file. Deleting documentation because a config line changed is not a
   trade anyone agreed to, and "extra folder" is a finding nowhere in this kit.
4. **The byte-identical sample gate covers one branch of four.** True — it renders
   one fixture, which takes one path. Every branch is asserted in CI instead: the
   exact folder set per profile, a clean validate with no layout NOTE, no seed file
   leaking in from an excluded folder, and the union of all profiles equalling the
   shipped template tree, so a folder no profile can produce cannot ship for nobody.

### The read model follows the profile

A page that nags about a section the repo deliberately does not have would undo the
whole point. `current.html` renders §4 API contracts only when `docs/04_api/` exists,
and `index.html` lists only layer-3 folders that are actually there.

**Section numbers are now assigned in render order** rather than written as literals,
so an omitted section closes the gap instead of leaving a hole. This also fixed two
cross-references that had been wrong since 0.20.0: inserting §4 shifted everything
after it, and the two prose lines pointing at "§4" and "§5" kept pointing one section
to the left of what they meant. Neither the sample gate nor any check could see it —
both branches rendered fine, they just said the wrong number.

### The detector proposes; only the user declares

`docs_detect.py` used to be forbidden from acting on what it knew. It now prints
`owns-hint:` lines — each carrying its evidence on the same line, `owns-hint:
endpoints — go.mod declares github.com/gin-gonic/gin` — plus `module-dir:` and
`module-count:`, the two-deployables fact it has always computed and never said.

It still writes nothing. `docs-init` shows the hints, asks with AskUserQuestion, and
scaffolds the answer. That asymmetry is what makes generous hinting safe: an
unconfirmed hint costs one option in a dialog, a silent one would put a wrong fact in
a file that decides the shape of the tree. Verified on five real repos — the Next.js
monorepo from 0.22.1 gets `data` (mongodb) and `screens` (next), which is exactly what
its architecture doc declares by hand.

### Fixed

- **`--sync` resurrected seeds somebody had deliberately deleted.** Deleting the
  example file once the real document is written is the documented thing to do, and
  the next sync brought it straight back — the rule was "copy any template file the
  repo lacks", and a deleted file is lacking. The rule is now **a seed arrives with
  its folder, never alone**: an existing folder is the repo's, and the only thing
  sync may put into one is nothing. A missing *folder* still returns with its seed.
  Found by running this release on a real Express repo, not by any test.
- **The design fixture never had an `04_api/`.** Shipped in 0.20.0, and every design
  sample since has shown "NO API CONTRACTS" — an empty state standing in for the
  section's real render. The byte-identical gate therefore covered neither the
  operations table nor the drift table, which is the whole of item H. The fixture now
  carries a contract with a matching `openapi.json`, so the samples show the state a
  healthy repo is in.
- `sensitive_paths`' fnmatch paragraph had drifted to the bottom of §9, under `owns`,
  where it read as a rule about profiles.

### What this does not claim

The measurable saving is close to zero. An empty folder costs no tokens: the renderer
skips it, `INDEX.md` has no line for it, no agent opens it. What F buys is a tree that
does not describe a repo the user does not have — a cognitive cost, not a token one.
Whether that was worth removing an invariant for is a question only real use answers,
and the honest position is that nobody has complained about empty folders yet.

## [0.22.1] — 2026-08-10

### Fixed — two things a real repo found that the fixture could not

Everything from 0.18.0 to 0.22.0 was tested against a fresh scaffold, the design
fixture, and CI mutations. Running it on a real Next.js repo — a monorepo with a web
app and a Zalo mini-app, 12 route handlers, MongoDB — found two defects immediately.
Both are false-positive classes, which is the failure mode that gets a warn-only check
switched off.

**`[id]` was not normalised.** Next.js and SvelteKit name route folders `[id]`, so
copying a route path into an `api` fence is the obvious thing to do. `norm_op` folded
`{id}` and `:id` but not `[id]`, and the contract went from clean to **four findings
caused by nothing but spelling**. It now folds all three.

**`NOTE [profile]` was looking at the wrong evidence.** The only signal wired was
"a folder holds documents", so a repo that obviously owned screens — it declared
`mini-app [ui]` right there in its architecture — produced no note at all. A
component's `[kind]` tag is far stronger evidence: it is the repo saying in its own
layer 1 what it holds, with a path to prove it. `[db]` now implies `data`, `[ui]`
implies `screens`, `[queue]` implies `jobs`, alongside the folder rule for `endpoints`.

### What the trial confirmed

Worth recording, because the point of the trial was to find out:

- Two architecture documents merged correctly, each component card naming its owner,
  and the cross-deployable edge (`mini-app -> api`, owned by the caller) rendered in
  the single graph. Item D holds on a real monorepo.
- `--check-api` matched **13 of 13** real operations against an OpenAPI spec generated
  from the actual route handlers, and caught the one endpoint planted to be missing.
  No false positives on a real API surface.
- `NOTE [stale]` fired on `web.md` alone when `lib/db.ts` was touched — the document
  that names the path — and stayed silent on `mini-app.md`. `FAIL [anchor]` caught a
  `git mv` of a real module.
- `docs_detect.py` read both manifests, including `mini-app/package.json` at depth 2.

One observation left unactioned: the detector sees two manifests and therefore knows
the repo has two deployables, but says nothing about it. That is the `scope` axis
sitting in data the detector already has, and it stays unused until F.

## [0.22.0] — 2026-08-10

### Added — `/docs-kit:docs-upgrade` and `docs_scaffold.sh --sync`

Everything shipped today changed what a scaffold contains — `_archive/` and `INDEX.md`
in 0.18.0, `04_api/` in 0.20.0 — and a repo scaffolded before them had no way to catch
up. `docs-init` refuses to touch an existing `docs/`, correctly, and its "add missing
pieces only" branch was **an instruction to an agent to run `cp -Rn` carefully**. A
careful file operation belongs in a script, not in a prompt.

`docs_scaffold.sh --sync` adds what is absent and never overwrites, edits, or deletes:
an existing file is the repo's content, and the script has no way to tell an edited
template from a deliberate rewrite, so it does not get to guess. Idempotent, and it
refuses a repo with no `docs/` rather than half-scaffolding one.

`/docs-kit:docs-upgrade` is the whole job around it — sync, regenerate the read models
(not optional: the sync may add documents, and a stale `INDEX.md` is worse than a
missing one), then re-run all three checks. It says out loud that **a newer standard
checks more than the old one did**, so `FAIL [anchor]` lines on an upgraded repo are
pre-existing drift being surfaced, not damage the upgrade caused. It changes no content
and routes every finding to whoever should fix it.

Six skills now; five still carry `disable-model-invocation: true`, so the always-on
context budget is unchanged — `brief` remains the only one Claude can reach on its own.

### Added — `owns` in `.docs-kit.json`, and the answer to "when does it get updated?"

Asking what a repo owns once at scaffold time would have been a mistake: that is state,
and state drifts. A backend grows a frontend; a service stops owning its tables.

So `owns` gets the treatment the kit already gives `verified_at` and `generated_from` —
**declare it, and let something deterministic notice when reality disagrees.** The
validator emits `NOTE [profile]` when a folder holds real documents that `owns` does not
account for. Optional throughout: a repo that omits it behaves exactly as before.

Two deliberate limits:

- **A file byte-identical to its shipped template is a seed, not content.** Without that
  rule the check fires on a fresh scaffold, because `04_api/example-api.md` ships with
  the plugin — and a warn-only rule that cries wolf on day one is a rule people switch
  off. Compared by bytes, not by name: `60_fe-integration/overview.md` has no "example"
  in its name.
- **Only the growth direction is checked.** `owns` claiming something the repo no longer
  has cannot be told apart from "nobody has written it yet". Guessing there would cry
  wolf, and the shrink direction runs into the unsolved deletion hole anyway.

Changing `owns` is a layer 1 change — what a repo owns is architecture — so it goes
through the Decision workflow, and `docs-upgrade` adds whatever folders the new `owns`
justifies.

This is the measurable half of item F. The breaking half — branching a fresh scaffold on
a detected profile — is deliberately still not done: the `scope`/`owns` axis was derived
from six repo shapes reasoned about, not six repos measured, and `NOTE [profile]` firing
(or not) on real repos is what turns that into evidence cheaply.

## [0.21.0] — 2026-08-10

### Added — `generated_from:`, the volatile half read instead of maintained

Item H, and it arrived much narrower than the proposal described it — deliberately.
The proposal imagined docs-kit *generating* the volatile half of a contract from route
tables. That was wrong: producing it means knowing the framework, Gin is not Express is
not FastAPI, and `docs_detect.py`'s whole discipline is to read declared facts rather
than infer them from a layout. **docs-kit consumes a standard artifact the repo already
produces. It does not generate one, and it should not.**

An `04_api/` doc may point `generated_from:` at `openapi.json` or a `*.proto`. The
renderer reads it at render time and prints the real operation list beside the
hand-written intent, marking each operation `matched`, `artifact only`, or
`documented only`. The sync cost of that half is zero, because nobody maintains it.

That is what makes the intent half worth a Decision gate: the part that changes often
stopped being a document.

### Added — `--check-api`: the enforcement §6 asked for and never had

§6 has always said a code change touching an API contract needs a Decision first.
Nothing could tell that the change had happened. Now something can:

```bash
docs_render.sh --check-api .     # 0 = match · 1 = drift, or the artifact is unreadable
```

Two findings, and they are not the same problem:

- **live but undocumented** — the §6 trigger firing after the fact. An endpoint shipped
  without going through the gate.
- **documented but absent** — the contract states something untrue.

An unreadable artifact fails too. A gate that quietly does not run is the failure this
gate exists to prevent — the same reasoning that made `INDEX.md` staleness a hard exit
in 0.18.1.

### Three constraints, each a consequence rather than a preference

- **OpenAPI must be JSON.** The floor is python 3.9 *stdlib*: it has a JSON parser and
  no YAML one. A hand-rolled YAML parser that misreads a contract is worse than one that
  refuses to read it, so a `.yaml` path fails with that sentence instead of a guess.
- **Events are excluded from the comparison.** OpenAPI describes no events, so counting
  an `event` line as missing would make the check cry wolf on every correct contract.
- **Path parameters are normalised** — `{id}` and `:id` are the same operation written
  by two tools, neither more correct — and `base` is stripped from both sides, so a spec
  that puts `/v1` in `servers` and one that puts it in every path describe the same API.

### Changed

- `generated_from` is an anchor, so `[anchor]` reports a moved artifact for free. No new
  check was needed; the mechanism added in 0.18.0 already covered it.
- `docs-check` runs all three read-only gates now — validator, `--check`, `--check-api`
  — and is explicit that these are more scripts, not more opinions.
- An unknown flag exits 2 instead of being silently treated as a repo path.

## [0.20.0] — 2026-08-10

### Added — `04_api/`, because §6 contradicted itself

Item E. The trigger table in §6 has always read *"code change touches a schema, **API
contract**, or component boundary → a Decision must already exist"*. The only place an
API contract could live was `60_fe-integration/` — layer 3, of which §4 says *"Edit it
directly. No traceability fields, no Decision needed."*

The standard demanded a Decision for a thing it gave nowhere to record. That is not a
gap in coverage, it is a contradiction, and it is why "thiết kế API thế nào" had no
answer in a model that otherwise specifies everything.

`04_api/` is layer 1: `service`, `protocol` (`http` | `grpc` | `graphql` | `event`),
optional `base`, plus the same `amended_by` / `rejected` / `verified_at` as Architecture.
Sixteen folders now, not fifteen. The PostToolUse hook guards it like the other two
layer-1 folders — otherwise the folder the Decision gate exists for would be the one
nothing watches.

**`service:` must name a component declared in `02_architecture/`.** That is the single
join between the folders and the validator enforces it under `[ref]`: a contract attached
to no service is worse than no contract, because the boundary then looks documented and
is not. Skipped while the architecture declares no components, so a fresh scaffold passes.

### Added — the ```` ```api ```` fence, and why it renders as a table

| line | meaning |
|---|---|
| `title:` `base:` `code:` | optional headers |
| `<VERB> <path>` | one operation |
| `event <name>` | an event this service publishes |
| `<- <Type>` · `-> <Type>` | what it accepts · what it returns |
| trailing ` — <gloss>` | explanation, the shared separator |

Every other fence draws because it carries a shape — a sequence, a lifecycle, a set of
relations. **A list of operations has none.** Drawing it would spend a figure number to
put boxes around a table, when §10's own rule is that the table carries the words. So
`api` is the first figure fence that renders as a table, and that is the design.

Unparseable input falls back to its source text, like every other fence: a contract
nobody can parse must never be displayed as one somebody can.

### The grammar is deliberately minimal, and that is the point

No status codes, no field types, no payload schemas. Those are the **volatile half** —
generated better than written, and stale within a sprint once hand-copied. Putting the
volatile half behind the Decision gate is exactly how a gate gets routed around, which
was the largest risk this item carried (recorded as limitation 3 in §9.2 of the
proposal).

What lives here is the half no generator can state: which operations exist at the
boundary, what each one means, and what the service deliberately does **not** expose.
That changes rarely, which is what makes it worth a Decision. The template ships
`## Không expose` and `## Compatibility` sections for exactly that content.

### Changed

- `current.html` gains §4 API contracts, right after Architecture; Business flows,
  Business logic and State machines shift to §5, §6, §7. The sidebar lists each
  contract by service.
- `INDEX.md` gains an `04_api` section — file, service, protocol, and the operation
  count, so an agent can tell whether a contract is worth opening.
- The lane test's first question widened from "does this modify the Architecture doc"
  to "does this modify a layer 1 doc — Architecture, Business logic, or an API contract".
  It always meant that; `04_api` made the omission visible.
- `docs-init` gained a step for writing contracts, `docs-sync`'s drift list gained the
  endpoint case, and both the digest and the CLAUDE.md snippet name the new folder.

## [0.19.0] — 2026-08-10

### Fixed — the renderer read one architecture document and silently dropped the rest

`02_architecture/` has always been a folder, and the validator has always globbed it.
The renderer opened `docs/02_architecture/architecture.md` and nothing else. So a repo
that split its architecture per service — the shape a monorepo of services actually
needs — had those documents **vanish from the sheet while `docs-check` called the tree
clean**. Rename the file and §3 rendered empty.

`build_current` now merges the folder: one component list, one data-flow graph, every
ERD and class block in document order, merged `tech_stack`, `constraints` and
`amended_by`. `main()` derives the component count and revision letters the same way.

Merging is not a compromise; it is what the ownership rule buys. A component belongs to
the document that declares it and an edge to the caller that declares it, so no fact is
written twice and re-assembling them reconstructs the system.

**With a single architecture document the output is byte-identical** — verified against
`design/sample-*.html` before and after the refactor.

### Added — item D of the cost proposal: one architecture document per service

STANDARD §4 now states the split and, more importantly, where each fact goes:

| Fact | Document |
|---|---|
| a component | the service that contains it |
| a table | the service that owns the writes |
| an edge `a -> b` | **`a`, the caller** — a dependency is a property of the thing that has it |
| the contract behind it | `b`, the callee |

Without that rule a split just duplicates: the edge `orders -> billing` looks like it
belongs to both. This is the same argument that makes ERD cardinality derived from `fk`
and a component card's `role` derived from `data_flow` — one source per fact.

The ERD was already following this by accident. A schema is only correct scoped to its
owner, and one fence holding every service's tables blows §10's 10-table budget while
saying nothing about who owns what. §10's wording moved from "the `02_architecture/`
doc" to "an `02_architecture/` doc" accordingly.

Each component card names the document that declares it (`owner`), and §3's source tag
reads `docs/02_architecture/ · N docs`. Both appear only when there is more than one
document, which is what keeps single-document output unchanged.

`docs-init` gained a step before it writes anything: decide how many architecture
documents this repo needs. `docs-sync`'s drift step gained the cross-document case — a
new service is a new document, and a new call between two services goes in the caller's.

### Added — `[ref]` now catches a component name declared twice

A component name **is** a reference key: `data_flow` edges name components and the
rendered cards resolve upstream/downstream by name. Two documents declaring `store` make
every edge touching it ambiguous, and the renderer resolves it by taking the first —
silently. It is now reported under `[ref]`, for the same reason a duplicate `id:` is.
The validator's `component_names()` mirrors the renderer's `parse_components()` so the
two agree on where a name ends.

### Fixed — an unrendered branch still referenced the old single-document variable

The "could not parse `data_flow`" fallback still read `arch_fm`, which the merge removed.
The design fixture parses cleanly, so that branch never runs there and the
byte-identical sample gate could not see it — a reminder that the gate proves the taken
path and nothing about the others. Found by rendering a tree with a deliberately
unparseable edge.

## [0.18.1] — 2026-08-10

### Added — `docs_render.sh --check`, the gate that makes the index safe to trust

0.18.0 made skills read `docs/INDEX.md` instead of globbing folders, and said in three
places that a stale index is worse than a missing one because the next agent trusts it.
It then shipped nothing that would notice. `docs-sync` was told to always re-render, but
anyone editing markdown and committing directly walked straight past that.

`--check` writes nothing, rebuilds the index in memory, and compares: `0` current, `1`
missing or stale, `2` no `docs/`. It goes through the same code path a real render uses,
so it cannot disagree with one — there is no second description of what the index should
contain. Only `INDEX.md` is checkable this way; the HTML pages embed a generated-at stamp
and a git ref and differ every run by design.

Wired into `/docs-kit:docs-check` as a second deterministic script — explicitly *not* a
second opinion; that skill's "report what the script said, add nothing, fix nothing" rule
is unchanged. Target repos get the one-liner in `docs/README.md` and the project README.

### Fixed — the wrapper swallowed the repo root whenever a flag came first

`docs_render.sh` forwarded only `"${1:-$(pwd)}"`, so `docs_render.sh --check <root>` checked
the *current* directory and reported on the wrong tree. It now forwards `"$@"`; the Python
side already defaulted to the current directory when given no root. Caught by the new CI
step on its first run, which is the argument for writing the test alongside the feature.

### Fixed — `docs-render` did not know `INDEX.md` exists

The skill that regenerates the read models reported three files and named only the HTML.
The script always wrote the fourth, so nothing was wrong on disk — but the skill would have
told the user the index was not part of what it just refreshed.

### Added — CI proves the gate works

A stale index must be caught, and `--check` must write nothing while catching it: the new
step renders, adds a document without re-rendering, asserts the check fails, and asserts
the checksums of every generated file are unchanged.

## [0.18.0] — 2026-08-10

### The model was optimising the cheap half of its own cost

Four questions started this: Issues/Backlog/Decisions pile up and burn tokens; the content
keeps getting longer; the things that actually matter (database, data paths, API, service
relationships) are never addressed concretely; and the scaffold should adapt to what kind of
product the repo holds. Splitting the lifetime cost of a docs set four ways — write, read,
verify, repair — showed the first two were being paid at the read step and the larger two
were not being addressed at all. This release lands the read-cost work and the first half of
the verify work. The rest is written up in [DESIGN-NOTES.md](DESIGN-NOTES.md), including a
self-assessment of what these changes still do not fix.

### Added — `docs/INDEX.md`, the read model for agents

The three HTML pages are the read model for people. Nothing was the read model for the
agent, so skills read whole folders: `brief` globbed all of `22_decisions/` to learn what was
settled, `docs-sync` globbed all of `23_backlog/`. That is one entire file per document, for
an answer whose size does not grow — while the folder's does, forever.

`docs_render.py` already parsed every one of those documents to build `changes.html`, so the
index costs nothing new to produce: one pipe-delimited line per document — id, status, refs,
file, description — grouped by folder, sorted, deterministic. Skills now read it and open only
the ids they need, and both skills say so as a rule rather than a suggestion.

The header is a fixed cost, so the saving is unremarkable on a fresh scaffold and large on a
real repo. That asymmetry is the point: the problem only exists at the second size.

**A stale index is worse than no index, because the next agent trusts it.** Regenerating is
therefore no longer optional in `docs-sync` — the step that used to say "skip silently if the
HTML views don't exist" now states that a skipped render leaves `INDEX.md` behind the
markdown, and says what skills must do until it is regenerated.

### Added — `_archive/`, so terminal documents leave the hot set

A Backlog item at `done` with its audit line written can never change again, but it kept
costing exactly as much to read as an open one. Each layer 2 folder may now hold an
`_archive/` subfolder for documents whose chain has completed.

The design had already cleared the way and never used it: §3 has always guaranteed that file
names are not reference keys, so moving a file breaks no reference. Use `git mv`.

**Archiving lowers read cost. It never lowers the standard.** The validator walks `_archive/`
exactly as it walks the folder above it, and CI proves it: a dangling ref inside `_archive/`
is still reported. Without that, "archive it" would become a way to launder a broken document.
Layer 1 is never archived — it is state, not history, and a component that no longer exists is
removed by a Decision.

### Added — `rejected:`, because layer 1 could not say what the system deliberately is not

`brief` was not being lazy when it read every Decision. A Decision with `outcome: rejected`
holds information that appears nowhere in layer 1: the architecture doc says what the system
*is*, never what was considered and dropped. So "read the index instead" would have been a
blind spot rather than a saving.

Architecture and Business logic now take an optional `rejected: []`, written by the same
Decision workflow that writes `amended_by`, and validated by the same rule — each entry must
cite an existing `DECISION-NNN`. With it, reading layer 1 alone is *correct*.

Both new fields are optional. A repo scaffolded before they existed stays valid; that is why
they arrived optional rather than required.

### Added — `[anchor]` and `NOTE [stale]`: the anchors that were already there

Every load-bearing fact in layer 1 has always carried an anchor into the source — a component
names its `` `path/in/repo` ``, every figure fence takes a `code:` header. **Nothing used
them.** `docs_validate.sh` checked that `components:` was *present*, never that anything it
named existed.

Two checks now do, and the split between them is deliberate:

- `FAIL [anchor]` — a named path no longer exists. Not a matter of opinion: the document
  cannot be verified against anything.
- `NOTE [stale]` — the doc carries `verified_at: <rev>` and some of the paths it names have
  changed since. Changed is not the same as wrong, so this warns, on the same reasoning as
  §8's warn-only hooks: blocking on a false positive teaches people to switch the check off.

The comparison is against the **working tree**, not HEAD. `docs-sync` runs before the session
is committed; comparing against HEAD would hide exactly the changes that session just made.

This is the mechanism by which docs become synchronised to a specific version, and it costs
zero tokens — a filesystem test and a `git diff`. It also bounds the expensive half:
`docs-sync` step 5 used to re-read Architecture in full every session and now reads code only
where these two lines point.

`[anchor]` does not make the validator check truth. It verifies that a named path exists,
never that the sentence about it is still correct — the most valuable sentence in layer 1
remains the one nothing can check.

### Fixed — the templates and the design fixture were both lying, and the new check said so

Turning `[anchor]` on failed a fresh scaffold immediately, which was the check working:

- `03_business-logic/business-logic.md` shipped `code: src/refund/approve.go` and
  `code: src/order/state.go`, files no scaffold creates. They are now `<placeholder>` values,
  consistent with the `erd` and `class` fences that always used them. Values containing `<` or
  `>` are skipped, which is what lets a fresh tree pass clean.
- `design/fixture/make-fixture.py` wrote `docs/` "and nothing else" while its architecture doc
  named five components and six `code:` paths — so the committed samples rendered a
  **`docs-check clean`** badge over a tree where ten anchors pointed at nothing. The fixture
  now writes the stub source tree those docs name. A design contract that displays a green
  badge for an unverifiable tree is worse than one that displays nothing.

Also fixed in passing: `design/sample-*.html` were stamped `render v0.15.0` while
`plugin.json` said `0.17.1`, so CI's "samples are reproducible" gate had been failing on main.
Regenerating for this release clears it.

### Changed

- `md_files()` reads a folder's `_archive/` subfolder too, and every loaded document carries
  an `archived` flag. Archived documents stay in the HTML and in `INDEX.md` (with an
  `_archive/` prefix on the file column) — hiding them would end a trace chain in an id the
  renderer cannot resolve.
- `load_docs()` gained an `architecture` key; the index needs it and nothing else changed.
- New `fm_list()` helper in the validator, shared by the amended-by and anchor checks, so the
  two cannot disagree about what a list entry is.
- `docs-init` step 3 now sets `verified_at` after reading the source, and `docs-sync` moves it
  forward only for documents it actually re-read.
- CI gained three mutation tests: a moved path must fail while placeholders stay silent, a
  dangling ref inside `_archive/` must still be reported, and `INDEX.md` must be byte-stable
  across two renders and contain every id in the tree.

## [0.17.1] — 2026-08-06

### Fixed — two sources of truth for one partition, and the executing copy was the unguarded one

0.17.0 told Step 6 to compose the workflow script "from this brief" — right in intent, too
loose in wording. Nothing stopped the composed script from arriving at a different split than
the ownership table in section 3, and when those disagree the copy that actually runs is the
script, not the table the user approved. That is the same defect this skill already refuses
elsewhere: a second copy of a decision is the copy that goes wrong, and the docs are the
source of truth.

Composing is now stated as translation, not a second design pass. The script derives its
partition from section 3 and never decides one; a script that wants a different split is
wrong, and a real disagreement is grounds to re-ask rather than to run the better-looking one.

## [0.17.0] — 2026-08-06

### Changed — the brief composes its own workflow instead of feeding a fixed one

0.16.0 shipped `workflows/brief-fanout.js`, a static orchestration script the skill called by
name. It is gone. The partition differs for every brief, so a fixed script could only ever be
a worse restatement of what the brief already says — and the brief says it well: sections 3,
4 and 6 carry scope, split strategy, shared files, the ceiling and the check, which is exactly
what a workflow script has to be written from. The brief **is** the input.

Step 6 now composes the script inline from the brief and runs it as a dynamic workflow, which
the user can watch with `/workflows`. The four properties that made the static script worth
having are stated as requirements on what gets composed: re-check the partition in code before
spawning anything (a prompt saying "do not collide" is a request; a partition rejected before
any agent starts is a fact), one agent per deliverable carrying its own exhaustive path list,
an independent verifier that reads files rather than the builder's report and fails closed,
and structured results naming every blocker, every shared-file need, and everything a cap
dropped.

## [0.16.0] — 2026-08-05

### Added — a brief can now say how the work splits, and run it that way

`skills/brief/SKILL.md` described work for exactly one receiving agent. Held against the
five things a usable orchestration input carries — scope, split strategy, verification,
output format, budget — it scored one met, two partial, two absent. Output format was its
strength. Scope bounded *authority* ("what may the agent not change") but never *paths*, and
could not express a read-only pass. Verification was the agent checking its own work. Split
strategy and budget were missing outright.

Four of the five are properties of *coordinating* work rather than of the work itself, which
is why a skill written for one agent never grew them — and why they now appear **only when
the work is actually being split**. A serial brief pays for none of it: path ownership and an
independent checker exist because two agents can collide, and one cannot. Phase 2 carries
them in existing sections: scope and split strategy as the `agent → deliverable → exact
writable paths` table in CONCRETE ASKS (with a read-only flag, so an inspect-first pass is
expressible at all), shared files and the agent ceiling in HARD CONSTRAINTS, the independent
checker in EXPECTED OUTPUT, and the blocked-agent rule in EDGE HANDLING.

The fifth is not conditional. `how to verify it` was too weak standing alone, so **every**
section 6 must now name what makes the result fail and must fail closed — a criterion nobody
could confirm is a failure, never a pass. That is a writing rule costing no dialog, because
acceptance criteria belong to the work; only *who runs the check* depends on how the work is
staffed.

The gate sits at the end of Phase 2, after CONCRETE ASKS is drafted — the first moment real
deliverables exist, so options are concrete partitions instead of the bare Yes/No the gate
rule forbids, and early enough that ownership boundaries still reach HARD CONSTRAINTS.
**Both dialogs propose rather than ask.** The skill has just written the brief and run the
disjointness test, so it already knows the paths and the counts; options lead with the
derived answer carrying real numbers, and AskUserQuestion's own free-text entry is what lets
the user override or extend it. Asking a user to *list* their write paths or acceptance
criteria is homework handed back — the same failure this skill exists to prevent, one level
up.

The skeleton stays at six sections — every piece has a home. The ownership table goes in
CONCRETE ASKS, the SHARED FILES list and the agent/spend ceiling in HARD CONSTRAINTS, the
blocked-agent rule in EDGE HANDLING, the independent check in EXPECTED OUTPUT.

Two rules exist because a split brief is read by a fleet rather than a reader. A ceiling is
**mandatory** in a split brief: without one nothing the brief says bounds how far the work
fans out. And section 5's escape hatch inverts — everywhere else it must name
AskUserQuestion, but a fanned-out agent has no such tool, so "end the turn" inside one means
it returns quietly while the others keep writing. In a split brief the agent records the
blocker and stops work on that deliverable instead.

**A size floor comes before the dialog.** Count the independent deliverables and the distinct
paths they write; below three deliverables or three paths the question is never asked and the
brief runs serially without comment. Fan-out costs a dialog, a partition to check, N agents
each re-reading the brief, a merge to supervise and a verification pass — under a small brief
that exceeds the wait it saves, and a dialog offered on a two-file change is how a user
learns to dismiss the dialog on the change that mattered. When the question *is* asked, the
counts go in the option labels, so the user answers from real numbers rather than a guess.

**A parallel answer then collects three parameters in one dialog and executes.** Mode
(inspect-first, where every agent reports what it *would* change and writes nothing — the
cheapest way to find a bad partition, since a wrong split costs a report instead of a merge),
ceiling, and whether each deliverable gets an independent verifier. A new workflow script
`workflows/brief-fanout.js` runs it, invoked as `docs-kit:brief-fanout`.

**The script re-checks the partition in code before spawning anything**, refusing on
overlapping paths, on a write into a shared file, and on a deliverable whose paths cannot be
enumerated. The duplication is the point: a prompt saying "do not collide" is a request, a
partition rejected before any agent starts is a fact. Three findings, each verified against
this repo rather than assumed, shaped the rest —

- **No agent gets an isolated worktree.** `briefs/` is gitignored with no tracked files
  (`git ls-files briefs/` returns 0), so a worktree starts without the directory and
  silently destroys the brief, reintroducing the exact defect 0.15.0 shipped to fix. Proven
  disjointness is what makes isolation unnecessary.
- **The caller pre-allocates every id as a literal.** `grep -rh '^id:' docs/` + 1 is
  read-then-write with no lock, and per-agent views of `docs/` make collision certain rather
  than likely — with the repair path closed by `references/issue-capture.md`'s own "never
  renumber an existing id".
- **A blocked agent records the blocker and stops that deliverable.** Fan-out agents have no
  AskUserQuestion, so "end the turn" inside one means it returns quietly while the others
  keep writing. The caller surfaces every blocker before merging, applies `sharedFileNeeds`
  serially itself, and runs the validator and renderer exactly once at the end.

Caps are never silent: the run reports what the ceiling dropped, what the guards rejected,
what failed verification, and any file written outside its ownership.

### Fixed — the gate with the most to settle was the one that broke

`skills/brief/SKILL.md` told itself two things that could not both be true. Step 2 of the
Phase 1 gate batches open decisions "up to 4 per call"; step 3 then said to *add one more
question to that same batch* in a `docs-kit` repo, for recording the Issue. AskUserQuestion
accepts at most 4 questions. So a gate that found 4 open decisions had 5 questions to ask,
and the file never reconciled it.

The consequence was not a dropped question. A 5th question makes the whole call invalid, and
a failed AskUserQuestion falls to step 4 — ask in plain text and end the turn. That is the
prose gate this skill spends five paragraphs forbidding, arriving precisely when the gate had
the most to settle. The Record question is also how consent to write into `docs/` is
collected, so losing the call loses the recording too.

Step 2 now says 4 is the tool's hard ceiling rather than a house style, and step 3 reserves
one of those slots instead of borrowing a fifth: at most 3 open decisions ride the first
call, and the rest go to the follow-up call step 2 already provided for. The reason is
written inline, per the skill's own technique (b) — without it, a future editor reads the
reserved slot as timidity and takes it back.

Found while analysing a proposed parallel-execution gate for the same skill; that analysis
shipped no behaviour change of its own.

## [0.15.0] — 2026-08-03

### Added — a brief now has a home, and the skill says what happens to it

`skills/brief/SKILL.md` used to end with one sentence about its own output:
*"Deliver the brief as a Markdown file the user can hand to the agent."* No path,
no owner, no lifecycle. In practice the file landed in whatever session scratchpad
the run happened to have, and stayed there. Seven of them had accumulated on the
author's machine — 136 KB filed across four different session ids under
`/private/tmp`, the oldest four days old — and a `grep` for cleanup logic across
`skills/`, `references/`, `hooks/`, `scripts/` and `STANDARD.md` returned exactly
one hit, which governs an abandoned Issue and not the brief file at all.

That is bad at both ends at once. The briefs accumulated, because nothing deletes
them; and they sat somewhere volatile, outside git and outside backup, filed under
an id nobody can read. The author had already worked around it by hand, keeping a
private `~/Projects/briefs/` the skill knew nothing about.

So the skill now states the contract it was missing. A brief goes to
`<repo-root>/briefs/` as `brief-<slug>.md`, and the full absolute path is printed
when the brief is handed over — a brief the user cannot find is a brief that was
not delivered. `briefs/` belongs in that repo's `.gitignore`, which makes adding
the line a write to a file the user owns, so it goes through AskUserQuestion like
every other such write; a repo with no `.gitignore` at all is a bigger act than
appending, and stops for a question of its own.

**`briefs/` is gitignored on purpose, and the reason is written into the skill so
nobody "fixes" it later.** A brief is the reasoning that led to a change, and this
file is where that reasoning belongs once the change lands. Commit both and the
repo carries two copies of the same decisions — and the brief, frozen at the
moment it was handed over, is the copy that goes stale.

**Nothing deletes a brief** — not the skill, not a hook, not `docs-sync`. The
temptation to add a sweep is exactly why the rule is stated rather than implied:
a brief records decisions that were already settled, so deleting it on a timer or
on "the work is done" throws away the *why* behind shipped code to reclaim a few
kilobytes. This is the same position Phase 1 already takes on an Issue left behind
by an abandoned gate.

`prompt-lessons.md` got the same treatment in passing. It was told to live *"in
the user's workspace"*, which is the identical defect seven lines further down;
it now sits in `briefs/` too, so one rule covers everything this skill writes.

## [0.14.1] — 2026-08-01

### Fixed — clicking `brief` in the menu no longer runs it with nothing to work on

`skills/brief/SKILL.md` now declares `argument-hint: "[what the work is about]"`
and `arguments: subject`. Both are needed, and they repair two different hosts.

In the terminal CLI, picking a command from the `/` menu writes `/name ` into the
input and then submits it, in the same breath — the only thing that holds the
submit back is the command declaring at least one named argument. `argument-hint`
does not qualify; it is display text. So a user who picked `brief` from the menu
intending to type a subject watched the turn start without one, and the skill fell
back to reading the subject out of whatever the conversation happened to contain.

The desktop app has no such brake. It runs the skill and injects an elicitation
block instead — `[Skill "brief" was invoked. It expects: …]` when the skill
declared a hint, and *"It did not declare an argument-hint, so infer what context
to collect from the SKILL.md instructions"* when it did not. The hint is the whole
difference between a turn that opens by asking and a turn that opens by guessing.

The other four skills are deliberately left alone. `docs-init`, `docs-check`,
`docs-render` and `docs-sync` genuinely take no arguments, so click-and-run is the
behaviour they want; giving them `arguments` would buy an extra keystroke and
nothing else.

### Changed — Phase 1's AskUserQuestion rule now says what it outranks

That same desktop elicitation block forbids AskUserQuestion and routes to the
`visualize` elicitation widget, which reads as a direct contradiction of Phase 1's
*"Resolve the gate with AskUserQuestion. Always."* The two govern different acts —
the host is collecting the **subject** before Phase 1 has anything to scan, while
the gate resolves **decisions** the conversation left open — and Phase 1 now says
so, along with why the obvious reconciliation is wrong: the widget is desktop-only,
and a gate that silently does nothing under the terminal CLI is worse than no gate.

### Removed — a helper pair that was never once called

`status_badge()` and `status_dot()` are gone from `scripts/docs_render.py`.
`git log -S'status_badge('` returns exactly one commit — 3550deb, the commit
that introduced `docs-render` — so the count went 0 → 1 and stopped there. The
one occurrence was the `def` line. It was never called, not even by the commit
that wrote it.

`status_dot()` did have a caller once, and lost it in 0.7.0. From then on the
two were a closed loop: `status_badge` was the only thing that called
`status_dot`, and nothing called `status_badge`.

The output was never wrong — `status_badge("docs-check clean", "live")` returns
byte-for-byte what the live code hand-writes. What replaced the pair is
`dot_html()`, and the reason is one line of vocabulary. `status_dot`'s sentinel
for *no modifier* is the empty string, so `status_dot("open")` emits a `d-open`
class that no rule styles — and `"open"` is a real state name in `ISSUE_DOTS`
and `BACKLOG_DOTS`. `status_badge` patched around that at the call boundary
(`if dot != "open"`), which is the special case leaking out of the function.
`dot_html` moved it inside. Every call site followed the one that spoke the
domain's own words.

`design/sample-*.html` are byte-identical after the deletion, which is the
proof the code was dead rather than merely unreachable-looking.

## [0.14.0] — 2026-08-01

### Added — `brief` became the forward path into Layer 2

STANDARD §6 has always said *"Starting work that is not in the Backlog → create
an Issue before writing code"*. Nothing implemented it. `docs-sync` only ever
built the chain backwards — its Issues carry the line "Created retroactively …
the work was done before this Issue existed" — and the Stop hook only nags once
the session is over. Layer 2 had a back door and no front door.

`brief` was already standing at the right moment: people run it immediately
before handing work off, which is exactly when §6 wants the Issue. It already
ran a decision-freeze gate that built a table of everything still open, and it
already read `docs/` — but only to *cite* decisions, never to *record* one.

So the front door is `brief` with the writing side switched on, gated on one
directory test (`docs/20_issues/`):

| Phase | New behaviour |
|---|---|
| 0 | Detect. No `docs/20_issues/` → the skill behaves exactly as before and writes nothing but the brief. |
| 1 | The gate's dialog carries one extra question: record this work as an Issue? Yes → the Issue opens at `status: exploring` holding the open-decision table — or straight at `open` when the gate found nothing worth asking about. |
| 1.5 | Gate closed → the Issue reaches `open`, then the lane test. Fast lane creates the Backlog item and promotes the Issue; full lane stops and asks. |
| 2 | Section 2 of the brief cites `BACKLOG-NNN` / `ISSUE-NNN` / `DECISION-NNN` instead of paraphrasing them. |

`exploring` is load-bearing rather than decorative: an Issue whose gate the user
walks away from stays there, which is exactly what STANDARD §4 reserves that
status for — "raw research, not yet a real Issue". Nothing cleans it up, and
nothing should.

Full lane **asks**, it never refuses — stop and draft the Proposal, or hand the
work over with a no-Decision-covers-this stamp in HARD CONSTRAINTS. Blocking is
how a plugin gets uninstalled, which costs every bit of enforcement it had; §8
already settled this for the hooks and the same reasoning governs the skill.

`brief` keeps its model invocability — it stays the one skill Claude may reach
for on its own — because the rule being enforced is "no unconfirmed writes into
`docs/`", not "no automatic invocation". The confirmation sits on the write.

### Added — `references/issue-capture.md`

Creating an Issue is now written once and read twice: by `brief` going forward
and by `docs-sync` going back. It is procedure only — `STANDARD.md` remains the
contract, and the file points at it rather than copying its tables, because two
copies of a contract drift and then neither is authoritative.

It also carries the rule that keeps the Stop hook honest: instructional text is
loaded into the transcript, and that hook treats a concrete id as proof the
session engaged with the docs workflow. A literal id with digits sitting in a
skill file silences it in every session, permanently. Prose says `ISSUE-NNN`;
digits live only under `docs/`.

### Changed — a relation is not a flow, and gets drawn like one now

`svg_dag` was built for ```` ```flow ````, where an edge means data moving. Four
figure types later it was still drawing every edge that way, including the two
where an edge means nothing of the sort. A foreign key does not travel and a UML
generalization does not travel, so a curve out of the middle of a box said the
wrong thing about them twice over: it started nowhere in particular, and the
middle of a tall entity box is a column that has nothing to do with the key being
drawn. Three foreign keys into `orders` all ended at `y=221`; the column they
actually name sat 33px away.

`route="struct"` swaps the curve for orthogonal lines with real anchors. It is
paint, not layout — layering, the feedback arc set and the return lanes are the
same code either way, so *one layered-graph engine* still holds.

| Relation | Leaves from | Lands on |
|---|---|---|
| `erd` foreign key | the fk column's own row | the row it names |
| `class` field of a declared type | that field's own row | the target's header band |
| `class` extends / implements | the header band — it belongs to the type, not to a member | the target's header band |

One relation is one line, from its own row to its own arrowhead, with a vertical
lane of its own in the column gap. Nothing is shared, so tracing a line backwards
can only end in one box. The one exception is measured rather than chosen: two
arrowheads fit in a 26px header band, three foreign keys into a 20px primary-key
column do not, so below that threshold they converge on a trunk with junction
dots — every tail still carrying its own marker on its own row. Where a converged
trunk's members disagree on a symbol, it wears the one most of them carry, and
the minority fact — a nullable key's `○` — is left to the `null` flag in the
table beside it.

Two coincidences that geometry alone would have shipped are now assertions. Two
relations leaving one header band no longer leave it at the same `y`, which used
to paint the dashed line over the solid one. And two feeders reaching a trunk
from opposite sides at the same `y` — a child's key and the parent's own key are
one coincidence apart — no longer draw a single unbroken line through the
junction that reads as "these two connect to each other".

A self-referencing key stops being a back-edge and enters its own box from the
side, which retires a 126px lobe below the rows and 15px of canvas.

### Changed — the ordering step Sugiyama has and this engine skipped

A column was ordered alphabetically: deterministic, and blind. It put
`SandboxAdapter` above `StripeAdapter`, so `extends BaseAdapter` had to climb
past everything the other one emitted, and no router could have helped — the fix
had to be the order. Each column is now ordered by the mean index of the nodes it
points at in the column to its right, sweeping right to left, ties keeping
alphabetical. Still reproducible byte for byte, still no iteration count to
converge. On the class figure it takes the best achievable crossings from 5 to 1.

This changes box order in existing figures, so it is the one change here that
`design/sample-*.html` could not absorb silently.

### Changed — arrowheads, and the constant that kept them off the box

Every marker in the renderer puts its tip on the path's own end point — the
chevron's point is at `viewBox x=8`, which is its `refX`; the triangle's apex at
12, which is its `refX`. `svg_dag` then ended every edge at `bx - 6`. So every
arrowhead in every figure stood 6px short of the thing it pointed at, while
back-edges below the rows already landed on the box. The rule that replaces the
constant: **an arrowhead's tip lands on the target's border.**

`markerUnits` defaults to `strokeWidth`, so a marker's real size is
`markerWidth ÷ viewBox × stroke-width`. Every flow arrowhead is `7 ÷ 10 × 1.6`;
the crow's foot and the UML triangle were written `12 ÷ 12 × 1.6`, 70% larger
than everything else on a 20px row pitch. Nobody chose that — it never got
compared. `MARKER_W` matches them by *ink* rather than by box, because the foot's
toes span 11 of its 12 viewBox units while the chevron spans 7 of 10. With a
19.2-unit foot the 6px gap read as part of the symbol; at 8.8 it read as a line
that stopped early. Shrinking the marker did not cause that defect, it exposed it.

### Changed — a flowchart says where it branches

Three shapes shared one 1.5px stroke on one white fill, so a chart that exists to
answer *where does this branch* gave the reader no way in. The diamond takes a
2px stroke and an `--l1-wash` fill and becomes the heaviest object on the page; a
step drops to 1.25px graphite and reads as ground; and the two ends stop being
identical capsules — the entry keeps full-weight ink, the exit is drawn light. No
new hue is spent: L1 was already the diamond's colour.

In the figure a class method is now `name(…)`. The full signature had been
printed once in the interface and once in every implementer — the same 46
characters six times — which drove each box to 467px and the canvas to 1012,
past `CONTENT_W`, so the right-hand column came out clipped. Fields keep their
types, and the signature keeps its own column in the table below.

### Changed — the tables under a figure

Six columns, horizontal rules only, the leading name repeated four to six times,
and about 40% of the cells an em-dash. Nothing held a column together for the
eye. Three devices, no row dropped — the table is still the figure's full
accessible reading: the repeated name becomes a band printed once; two vertical
hairlines cut each row into what it **is**, what it is **specified** as, and what
it **means**; an empty cell becomes a faint dot so it stops competing with real
text. `fk` moves back into the key column, where "what kind of key is this" is
actually answered.

A flowchart shipped two tables — a list of branch points and a list of edges —
and between them they never answered the question a reader arrives with: *at this
branch point, how many ways out, and where does each go.* They are now one
decision table, banded by source. A state machine is the same table with the same
shape: the band is the state and its meaning, the rows under it are the
transitions out of it, and a final state keeps its meaning with an explicit note
that it has none.

### Changed — the design contract caught up with the renderer

`design/design-system.html` stopped at v0.7.0, so the document that contracts
how figures look described none of the four figure types that arrived after it,
and two of its sentences had gone from stale to false — a scale rule splitting
graphs into `FIG 2a` / `2b` (deleted in 0.9.1, nothing replaced it) and column
order described as alphabetical. §6 now carries the four fences and what each
answers, the geometry a relation is drawn with, and what the table under a
figure is for. Its five figures are spliced from `design/sample-current.html`
rather than frozen in place, which is the actual fix for the drift: `FIG 2` had
been showing arrowheads standing 6px off their boxes underneath prose claiming
they land on the border.

Two mirror divergences surfaced while checking, both predating this work.
`.plot` had no `overflow-x`, so a figure wider than the column pushed the whole
page sideways instead of scrolling inside its own frame — the exact rule the
document states. `.lede` was 20px narrower there than in the renderer. A
scripted diff of the 157 shared selectors now reports no other difference.

### Fixed

- `README.md` described `/docs-kit:brief` as "Manual invocation only" and as
  writing no files. The second half is what this release changes; the first half
  had been stale since 0.9.0. `brief` really was manual-only back when it was
  `commands/brief.md`, which carried `disable-model-invocation: true`. Folding
  `commands/` into `skills/` dropped the flag and made `brief` the one
  model-reachable skill — the Invariants section was updated to say so, the
  usage table was not. Two descriptions of the same skill disagreed for a whole
  minor version.

## [0.13.0] — 2026-08-01

### Added — ```` ```class ````, the code's own contracts

The ERD says what the database holds. It says nothing about which type satisfies
which interface — and in a codebase whose architecture rests on "only
payment-adapter may call the PSP", that sentence is a claim about an interface
with more than one implementation, written down nowhere.

- **```` ```class ````** in the body of the `02_architecture/` doc, rendering in a
  new **Types & contracts** sub-section of §3 right after Data model. `class:` and
  `interface:` open a type; `extends` and `implements` are relation lines inside
  it; `+` and `-` mark visibility; a member containing `(` is a method and splits
  at the paren, not at whitespace — splitting on the first space yields the
  nonsense `Capture(orderID` / `string, cents int64) (Receipt, error)`.
- **Association is derived, never written.** A field whose type names another
  declared type draws its own edge, for the same reason `fk` draws an ERD
  relationship: one source per fact. `*`, `[]`, `...` and `map[…]` are stripped
  first, so `*http.Client` matches nothing — a type from another package is not in
  this picture. Method signatures are not scanned; one naming every type in the
  package would draw a graph nobody can read.
- **No composition, no aggregation.** The boundary between them generates more
  argument than insight, and hand-written it drifts from the code.

### Added — `scripts/docs_detect.py`, and `docs-init` uses it

Scaffolding a Go repo used to start from a blank `tech_stack:`. Now a read-only
detector reports what the manifests actually declare — language and version,
direct dependencies, docker-compose services and their images, which is where a
real `PostgreSQL 16` comes from, since no language manifest says it.

- It **writes nothing**. `docs-init` reads the report, asks, and writes — in the
  dialog Step 3 already had, because a trickle of dialogs is how a user stops
  reading them.
- **Only `tech_stack:` may be filled from it.** A manifest stating `go 1.22` is a
  fact; a component's description is a claim about behaviour, and STANDARD §4
  already calls `auth — handles auth` a failure.
- Every cap is printed. `dep:` stops at 15 per manifest and `dep-count:` states
  the true total, because a silent truncation reads as "that was all of them".
- `frontend: yes` is **reporting, not branching**. The tree is 15 folders for
  every repo; making it conditional would leave every backend repo printing a
  layout NOTE forever.

### Changed

- `svg_dag()` learned a `"sep"` row tag (a hairline above that row) and
  `entity_tag` (a stereotype inside the header band). A class box is the ERD's
  entity box with those two things — not a second kind of node — and neither
  changes any height.
- `implements` edges are **statically** dashed, graphite. Marching dashes already
  mean async or fast-lane, and a UML realization arrow is neither, so `svg_dag`
  gained an explicit `dashed` set rather than reusing the async flag.
- `docs-init` Step 3 now also asks for the ```` ```erd ````, ```` ```class ````,
  ```` ```flowchart ```` and ```` ```state ```` blocks. It had been telling agents
  to fill `components` and ```` ```flow ```` only — every fence added since 0.10.0
  was invisible to the one skill that populates a fresh repo.

## [0.12.0] — 2026-07-31

### Added — ```` ```erd ````, the data model

Architecture said what exists for services and what calls what. It said nothing
about the tables underneath, so the schema lived in a migration folder and in
whoever last read it.

- **```` ```erd ```` in the body of the `02_architecture/` doc**, rendered in a new
  **Data model** sub-section of §3 right after Components — because an ERD answers
  the question Components answers, one level down, for data instead of services.
  Read from that doc and no other: a data model filed under a product or a
  business rule is misfiled, and rendering it anyway would hide that.
- **`table:` opens an entity, one column per line**, flags in any order:
  `pk` · `fk -> t.c` · `unique` · `null`, plus the ` — gloss` every other fence
  already takes.
- **No relationship syntax, and no hand-written cardinality.** A foreign key *is*
  the relationship, and what it means is not a matter of opinion: many child rows
  point at one parent row. The child end takes a crow's foot, the parent end a
  single bar, `unique` makes the child end a bar too, `null` adds the empty ring.
  Writing that by hand would be a second source for one fact, and the picture
  would drift from the column list printed beneath it.
- A **self-referencing FK is an ordinary back-edge** on the return lanes from
  0.9.1. Nothing in this release routes an edge.
- `pk` / `fk` tags are graphite. They name no layer, so they buy no hue.

### Changed

- **`svg_dag()` now measures heights instead of multiplying by a row pitch.** An
  entity box is as tall as its table is long — the first node in the engine whose
  height is not `NODE_H`. Columns sum their members' heights plus a fixed
  `ROW_GAP`, vertical centring compares totals, and edge endpoints ask each node
  how tall it is. With every node one height the two forms are the same
  arithmetic, which is how the change was shipped as a proven no-op before any ERD
  code existed: the three existing figures re-rendered byte for byte.
- `svg_dag()` also gained `marks` (per-edge endpoint markers, either end allowed
  to be bare) and `defs` (raw `<defs>` from the caller). **It still does not know
  what a crow's foot is** — it places markers by id and `erd_figure` defines them.
  An edge with its own markers gets no gliding packet either: the packet means
  data moving, and a foreign key is a shape of the schema, not a flow.
- Figures on `current.html` renumber: the ERD is FIG 1, so the data-flow graph is
  now FIG 2. A consequence of where the section sits, not of anything else.

## [0.11.0] — 2026-07-31

### Added — ```` ```state ````, the entity lifecycle

0.10.0 gave branching rules a home. A rule tells you which way an order goes at a
decision; it does not tell you **where an order can be**. That list — `pending`,
`paid`, `shipped`, `refunded` — usually lives spread across an enum, a migration
and a handful of guard clauses, and nowhere written down whole.

- **```` ```state ````** in the body of any `03_business-logic/`, `01_products/`
  or `02_architecture/` doc. `initial:` and `final:` mark **real states** rather
  than adding `start` / `end` pseudo-nodes: a six-state machine has to show six
  boxes, and an `end` sink would need a fabricated edge out of every terminal
  state, inflating the figure and the transition table alike. States are rounded
  boxes; the start state takes a blue stroke; a final state takes a second border
  drawn **inside** the box, because an outer ring would push it past the column
  width every layout measurement is built on.
- **`state: <name> — <meaning>`, optional.** Declaring one state opts the file
  into a warning listing the ones still undeclared. It earns its place because a
  mistyped state reads as plausible — a stray box in a flowchart catches the eye,
  `shiped` sitting in a lifecycle does not.
- **§6 State machines on `current.html`**, its own rail station, and the
  transition table plus the state-meaning table under every machine.
- **No guard syntax.** A condition worth drawing deserves a ```` ```flowchart ````
  beside it, which is what §5 already is.

### Changed

- `svg_dag()` learned two shapes (`state`, `final`) and an `initial` argument.
  Loops came free: a retry, a return to the warehouse, a refund after delivery are
  ordinary back-edges on the return lanes built in 0.9.1 — a lifecycle is the
  cyclic case that machinery was written for.
- `seq_steps_table()` takes a `last_col` label instead of growing a second table
  function with identical columns. The `kind` column stays for state machines too:
  `~>` there means the move is made by a background job, not by the user.
- `decide:` and `state:` share one `split_decl()`, so the two cannot drift into
  two ideas of what separates a node name from the sentence explaining it.

## [0.10.0] — 2026-07-31

### Added — `03_business-logic/`, the fourth layer-1 folder

`data_flow` says what calls what. ```` ```flow ```` says what happens in what
order. Neither says **what happens when a condition holds** — a sequence has no
branches. That rule had nowhere to live, so it lived in people's heads.

- **`docs/03_business-logic/`** — layer 1, gated by the Decision workflow like
  Architecture, with its own two-field frontmatter (`domain`, `amended_by`). The
  scaffold is now **15 folders**. A repo scaffolded before this only sees an
  informational `NOTE [layout]`; nothing starts failing.
- **```` ```flowchart ````** — branch points declared with `decide: node — question?`,
  drawn as diamonds; steps in the edge grammar already used by `data_flow` and
  ```` ```flow ````; `start` / `end` as stadium terminals. There is deliberately no
  branch syntax: **a branch is an ordinary labelled edge**, so the layered engine
  places it by the same rule as every other label, and a retry loop is an ordinary
  back-edge on a return lane — both inherited from 0.9.1 rather than reimplemented.
  A branch label takes the diamond's own hue, spending no new one, because it is
  the most load-bearing text on the figure.
- **§5 Business logic on `current.html`**, its own rail station, and the numbered
  step table plus decide-question table under every chart.
- Decision tables stay **plain markdown tables**. A table is already a table; a
  grammar for it would have been a grammar for nothing.

### Changed

- `extract_flows()` → `extract_figures()`, a fence registry. Adding a figure type
  is now adding a name to `FIGURE_FENCES` plus its parser.
- The edge grammar moved into one `parse_edge_line()`, read by `data_flow`,
  ```` ```flow ```` and ```` ```flowchart ```` alike, so the three cannot drift into
  three dialects.
- `svg_dag()` gained a `shapes` argument and renders flowchart nodes through the
  same layering and back-edge routing as the data-flow graph — one engine, because
  two would mean maintaining that routing twice.

### Fixed

- **The architecture hook no longer fires on the plugin's own templates.**
  `templates/docs/02_architecture/` ends in the exact path the hook watches for,
  so anyone editing a shipped template got warned about a Decision that could not
  possibly exist — precisely the false-positive class that teaches people to
  disable a warn-only hook.

## [0.9.1] — 2026-07-31

### ⚠️ Removed — the matrix style is gone

`data_flow` had two presentations: a graph, and a source × target **matrix** for
flows that were dense *or cyclic*. The matrix is deleted. There is one style now,
and it is the graph.

The trigger, not the density, was the real problem. **A cycle sent any flow to the
matrix regardless of size** — a six-component API server with `cache -> api` and
`worker ~> api` was drawn as a 247×231 grid of nine dots, with every edge label
stripped off the figure and replaced by a marker meaning "look it up in the table
below". But request/response, callbacks, cache read-backs and retries are ordinary
shapes in a running system; treating them as an overflow condition punished the
common case.

The consolation the standard promised never arrived either. §10 said a matrix is
*"always accompanied by … a graph of each connected sub-flow that does fit"*, but
the code asked `len(group) < len(edges)` over **connected components** — and a real
system is connected, so there was exactly one group, the condition was never true,
and no sub-graph was ever drawn. What shipped was a bare matrix.

### Added

- **Back-edges.** Before layering, the renderer lifts out a *feedback arc set*
  (DFS from each root in name order; an edge into a node still on the stack is a
  back-edge), layers what remains, and draws the lifted edges back in on **return
  lanes below the rows** — narrowest run in the shallowest lane, so a short return
  nested inside a long one never has to cross it. A back-edge is told apart by its
  route alone: nothing else is drawn under the rows. That spends no new hue and
  keeps it distinct from the teal dashed async edges it may itself be one of.
  `a -> a` is a loop in its own lane. The caption states the count.
- The feedback arc set is not minimal (that is NP-hard) but it is **stable** —
  every iteration order in its computation is sorted, so the same input always
  lifts the same edges, and the rendered bytes stay reproducible.
- **The complete edge table is now printed under every flow figure**, not only
  under the ones that needed rescuing. The figure carries the shape, the table
  carries the words, and the table is the figure's accessible reading.

### Changed

- **The density budget stopped choosing a presentation and started choosing a
  warning.** With one style left there is nothing to switch to, so past the budget
  the graph is still drawn in full, at natural size, scrolling inside its own
  frame — with a note suggesting the flow be split across Architecture docs.
  Raised accordingly: **20 nodes · 32 edges · 10 per column** (was 12 · 18 · 7).
- `flow_groups()` was only ever called by the matrix branch and went with it.

## [0.9.0] — 2026-07-31

### ⚠️ Breaking — this plugin now installs switched off

`docs-kit` registers two hooks, `PostToolUse` and `Stop`. Hooks run without you
asking on that particular occasion, so the plugin ships `defaultEnabled: false`:
**a fresh `/plugin install` leaves it disabled** until you turn it on.

```
/plugin enable docs-kit@archi-ai-labs
```

Three things that are *not* affected:

- **Anyone already running `docs-kit`.** A choice recorded in `enabledPlugins`
  outranks this default, at every settings scope. Nothing flips.
- **The installer route.** `install.sh --plugins docs-kit` writes an explicit
  `true`, and naming the plugin is the decision this default was waiting for.
- **Claude Code before v2.1.154.** Those versions ignore the field and install
  the plugin enabled either way.

This is the judgement the marketplace installer has always made — with no
arguments it enables `trim-kit` only — moved into the plugin, where it also
covers people who never touch the installer.

### ⚠️ Changed — Claude reaches for one skill here, not four

Only `brief` stays model-invocable. `docs-init`, `docs-check`, `docs-sync` and
`docs-render` carry `disable-model-invocation: true`, which takes their
descriptions **out of context entirely** rather than merely locking the trigger.

What that costs: *"help me set up project docs"* no longer reaches `docs-init` on
its own. You type `/docs-kit:docs-init`. What it buys: the plugin's always-on
context cost is now **about 77 tokens**, one description, and the README states
that as a measured number.

`brief` was the one worth keeping open — someone assembling instructions for
another agent will not remember that a command exists for exactly that — and its
description is rewritten to name the situation rather than the feature, which is
what a description has to do to fire at all.

### Changed

- **`commands/` is gone; every command is a skill.** Three of its five files were
  six-line wrappers whose entire body said *"invoke the same-named skill"* — and a
  skill outranks a command of the same name, so **those three never ran**. They
  were dead files shaped like implementations. `brief` and `docs-render` held real
  content and moved to `skills/` with their history. The set of commands is
  unchanged: `brief`, `docs-check`, `docs-init`, `docs-render`, `docs-sync`.
- **Three descriptions stopped enforcing in prose what a flag enforces for free.**
  `docs-check`, `docs-init` and `docs-sync` each carried *"Use only when the user
  runs /docs-kit:…"* inside `description` — a sentence that rode in context on
  every turn to ask for the behaviour `disable-model-invocation` guarantees.
- **`plugin.json` carries the metadata a reviewer reads first** — `$schema`,
  `displayName`, `homepage`, `repository`, `license`, `author.url` — and CI runs
  `claude plugin validate --strict`.

### Fixed

- **`docs-sync`'s frontmatter would have shipped unparseable.** An unquoted
  `description` containing `: ` is a YAML mapping, not a string; the skill loads
  at runtime with **every frontmatter field silently dropped**. Caught by
  `claude plugin validate` before release, which is the argument for running it as
  a gate rather than a courtesy.

## [0.8.0] — 2026-07-31

### ⚠️ Breaking — the marketplace id changed

`docs-kit` moved to the `archi-ai-labs` organisation, and the catalog it ships in
moved into its own repo,
[`archi-ai-labs/agent-marketplace`](https://github.com/archi-ai-labs/agent-marketplace)
— it used to live at the root of `archimonde12/claude-trim-kit`, which meant the
marketplace was named after a person and hosted inside an unrelated plugin. The
marketplace is now called **`archi-ai-labs`**, so the install id is
**`docs-kit@archi-ai-labs`**. Existing installs do not migrate themselves —
remove the old one and install the new:

```
/plugin uninstall docs-kit@archimonde12
/plugin marketplace remove archimonde12
/plugin marketplace add archi-ai-labs/agent-marketplace
/plugin install docs-kit@archi-ai-labs
```

Or in one line from a terminal:

```bash
curl -fsSL https://archi-ai-labs.github.io/agent-marketplace/install.sh | bash -s -- --plugins docs-kit
```

`--plugins docs-kit` is required: the installer's default enables only
`trim-kit`, because `docs-kit` registers hooks and those are not switched on for
someone who did not ask.

### Changed

- **The README now follows
  [README-STANDARD](https://github.com/archi-ai-labs/agent-marketplace/blob/main/standards/README-STANDARD.md),**
  the frame every plugin in this marketplace shares. Four things were missing and
  are now present: a terminal install (Option 1) beside the in-Claude one, which
  the README previously had no way to offer; the installation appendix in full —
  how to read the script before running it, local dev, and the exact
  `extraKnownMarketplaces` / `enabledPlugins` JSON the installer writes; the
  manual uninstall route naming both of those keys and the `.bak` the installer
  leaves; and `/plugin marketplace remove` with its consequence stated. Nothing
  was removed — the model, generated views and enforcement sections stay as they
  were.
- **Project layout** now points at the real catalog repo instead of describing a
  marketplace hosted inside `claude-trim-kit`.

## [0.7.0] — 2026-07-31

### Added

- **A figure standard, written into STANDARD §10 and enforced in the renderer.**
  A figure is never scaled below its natural size — text shrunk to make a diagram
  fit is a diagram nobody reads. Figures wider than the column now scroll inside
  their own frame instead. The graph style has a published density budget
  (12 nodes · 18 edges · 7 per column; 8 lanes · 16 steps for sequences), and
  past it the renderer changes *style* rather than scale.
- **A second presentation style for dense flows: the matrix.** Over budget — or
  cyclic — `data_flow` renders as a source × target grid, which grows linearly
  where a graph's crossings grow quadratically, and which makes hubs visible as
  full rows. It ships with the complete edge table and with a graph of every
  connected sub-flow that does fit. A cyclic flow previously degraded to a
  bullet list; it now gets a real figure.
- **Business flows as sequence figures.** A ```` ```flow ```` fenced block in the
  *body* of any `01_products/` or `02_architecture/` doc renders as a sequence
  diagram — lifelines left to right, time down the page, participants ordered by
  first appearance, `a -> a` self-calls, async dashed teal, framed by optional
  `title:` / `trigger:` / `outcome:` / `code:` headers. They are collected into a
  new **Business flows** section on `current.html` rather than left buried in
  each card's collapsible. Deliberately a body fence and not frontmatter: the
  validator parses frontmatter with awk, and the flows belong next to the prose
  that explains them.
- **Component cards that say what a component is.** The entry grammar gains a
  backticked source path — ``name [kind] `path/in/repo` — what it does`` — and
  the card derives role, upstream and downstream from `data_flow` so nobody
  maintains a second copy. A `### <name>` section in the architecture body
  becomes that card's expandable detail.
- **docs-init Step 3 reads the repo's source** to fill components, data flow and
  business flows, with an explicit quality bar (`"auth — handles auth"` is called
  out as a failure). **docs-sync Step 5** compares the documented architecture
  against the code the session touched and opens an Issue on drift — it never
  rewrites layer 1 outside the Decision path.
- Open-source project scaffolding to match the house standard: `LICENSE` (MIT),
  this changelog, and `.github/workflows/validate.yml` — CI that checks the tag
  against `plugin.json`, lints the manifest, compiles the scripts on python 3.9
  (the portability floor), scaffolds and validates a fresh tree, asserts the
  validator still rejects a dangling ref, exercises both hooks, and fails if
  `design/sample-*.html` differ from a fresh render.

### Fixed

- **Roadmap bullets carrying an id lost their markdown.** One code path had three
  defects at once: the text was escaped rather than rendered, so `**WS3**` and
  `` `book` `` printed literally; ids were stripped with a bare regex that gutted
  a markdown link *and* its href, leaving `[](../21_proposals/-example.md)`; and
  refs were never deduped, so an id cited both as link text and inside the href
  produced two identical chips.
- **Edge labels could land on top of nodes.** Labels now live in the gap after
  their source column, and the gap is widened to hold them — overlap is
  structurally impossible rather than avoided by nudging. On a 13-node flow this
  took the count from 7 of 8 chips overlapping a node to zero. Labels over 17
  characters wrap onto two balanced lines to keep the gaps narrow.
- **A commented frontmatter field parsed as a string.** `parse_frontmatter` had
  no YAML inline-comment handling, so `components: []  # hint` — the exact form
  documented in STANDARD §4 — became a literal string, inventing a phantom
  component and a phantom flow edge on every fresh scaffold.
- **A ```` ```flow ```` example shown inside a ````` ````markdown ````` block was
  extracted as a real flow.** Fence scanning is now CommonMark-correct on fence
  length, so documentation about the syntax no longer renders as a diagram of
  placeholder text.

## [0.6.2] — 2026-07-31

### Changed

- **Product names are proper nouns.** The §1 sidebar read "Merchant Dashboard",
  "OrderHub API", "Đối soát giao dịch" — two English siblings and one Vietnamese
  one, which reads as a leak rather than a choice. The leak was in STANDARD §11,
  which classified `name:` as explanation and so had it translated; but `name:`
  is a nav target and a thing people say out loud, which puts it with the domain
  terms. §11 now states three rules instead: `name:` is a proper noun, names
  within one set keep one register, and the file name stays ASCII regardless.

## [0.6.1] — 2026-07-31

### Fixed

- **Translate the title, not the file name.** The v0.6.0 fixture filed a product
  under `đối-soát.md` to show that `slugify()` folds diacritics — demonstrating a
  case §11 forbids in the same release. The product keeps its Vietnamese title
  and moves to `reconciliation.md`; `slugify()` stays, reframed in its docstring
  as the safety net it actually is.

## [0.6.0] — 2026-07-31

### Changed

- **The language split reaches the templates and the fixture.** v0.5.0 translated
  the renderer's chrome but left every template in English, so a fresh scaffold
  handed the user Vietnamese explanations wrapped around English example content.
  All 14 templates, `docs/README.md`, the CLAUDE.md snippet and the orderhub
  fixture now follow STANDARD §11. Field names, enum values, id prefixes, roadmap
  column headings and `## Alternatives considered` stayed English — the renderer
  or the validator reads each of them literally.

### Fixed

- A regression from v0.5.0: `roadmap_kind()` turned a substring test into a prefix
  test, silently dropping the colour from roadmap columns whose heading did not
  start with the keyword.

## [0.5.0] — 2026-07-31

### Changed

- **Vietnamese explanations, English frame.** The generated views explained
  themselves in English while the docs they describe are written in Vietnamese.
  Structure stays English — folder and field names, enum values, id prefixes,
  domain terms, UI labels — and the 38 explanatory strings (ledes, notes, figure
  captions, empty-state hints) became Vietnamese. Written into STANDARD §11 so it
  is a contract rather than a habit.

### Fixed

- Two bugs that only Vietnamese input exposes, in anchor slugs and text measurement.

## [0.4.0] — 2026-07-31

### Added

- **Reproducible design samples.** `design/sample-*.html` are the shipped
  reference for what the renderer produces, but the recipe for regenerating them
  lived only in a scratch directory, so in practice they were unreproducible and
  drifted silently. `design/fixture/make-fixture.py` builds the fictional
  *orderhub* tree — which exercises every renderer branch — and
  `design/make-samples.sh` renders it and rewrites cross-page links so the three
  files browse as a set. Output is byte-stable: the fixture commit pins identity
  and dates, and `DOCS_KIT_NOW` pins the generation stamp.

### Changed

- **Colour became a budget, not decoration.** Four hue families spent by meaning:
  blue = Layer 1, violet = Layer 2, teal = the fast-lane bypass, orange =
  interactive or happening now. Green and red are stamped verdicts only; anything
  without a layer stays graphite; prose and tables never take a hue.

## [0.3.0] — 2026-07-31

### Added

- **Meaning-bearing motion in the diagrams** — pure CSS, zero JS. Exactly three
  animations: a white packet gliding along solid edges (data direction), marching
  dashes on dashed strokes (async / fast lane / amendment), and an LED pulse on
  live dots. No entrance or hover animation; `prefers-reduced-motion` disables all
  of it.

## [0.2.0] — 2026-07-31

### Added

- **`/docs-kit:docs-render`** — deterministic HTML views of `docs/`
  (`index.html`, `current.html`, `changes.html`), python 3.9 stdlib, no LLM and
  no network, styled per the "change-control print" design system. Same input
  docs produce the same output bytes.

## [0.1.0] — 2026-07-30

### Added

- Initial release: the three-layer docs model as an installable plugin —
  `docs-init`, `docs-sync`, `docs-check`, the `STANDARD.md` source of truth, the
  14-folder template tree, the deterministic validator, and two warn-only hooks.
- **`/docs-kit:brief`** — turns settled decisions into a delegation prompt for a
  coding agent, gating on a decision-freeze check first.
