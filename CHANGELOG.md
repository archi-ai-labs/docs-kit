# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions live in `.claude-plugin/plugin.json` (the single source of truth
for the plugin version — the renderer stamps it into every generated page).

## [Unreleased]

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
