# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions live in `.claude-plugin/plugin.json` (the single source of truth
for the plugin version — the renderer stamps it into every generated page).

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
