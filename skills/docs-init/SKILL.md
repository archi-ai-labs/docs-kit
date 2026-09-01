---
name: docs-init
description: The main entry point. Scaffold the three-layer docs structure into this repo — the folders this repo's profile calls for, templates, docs/README.md — and optionally wire the rules into CLAUDE.md.
disable-model-invocation: true
---

# docs-init — scaffold the three-layer docs structure

You are setting up the docs-kit three-layer documentation model in the **current
repository**. The full standard lives in `STANDARD.md` at the plugin root — the
scaffold below implements it; read it if any judgment call comes up.

**Language.** Write explanations in Vietnamese; keep the scaffolding in English.
Structure is English — folder names, frontmatter field names, id prefixes
(`ISSUE-`, `PROPOSAL-`, `DECISION-`, `BACKLOG-`), enum values (`open`,
`in-progress`, `done`, `approved`, `rejected`, `fast`, `full`), section headings,
and the domain terms themselves (Issue, Proposal, Decision, Backlog, Architecture,
fast lane, full lane). Everything that *explains* — descriptions, problem
statements, rationale, audit lines — is Vietnamese, with those English terms left
bare inside the sentence rather than translated. See STANDARD §11.

Templates are project-agnostic — never inject the current project's name into them.

## Step 0 — Resolve the plugin root

Resolve `PLUGIN_ROOT` in this order:
1. The `${CLAUDE_PLUGIN_ROOT}` environment variable, if set (`echo "$CLAUDE_PLUGIN_ROOT"`).
2. The directory two levels above this SKILL.md file (`skills/docs-init/SKILL.md` → plugin root).
3. `find ~/.claude/plugins -maxdepth 6 -type d -name docs-kit` and pick the match
   that contains `.claude-plugin/plugin.json`.

Verify: `$PLUGIN_ROOT/scripts/docs_scaffold.sh` must exist.

## Step 1 — Preflight: does `docs/` already exist?

Check for `docs/` in the repo root (current working directory).

**If `docs/` exists: STOP. Do not create, merge, or overwrite anything.**
1. Report the current state: which of the folders this repo's profile calls for
   are present / missing (the scaffold script prints exactly this if you run it —
   it refuses with exit 3 and touches nothing), plus any non-standard entries.
2. Ask the user with AskUserQuestion — question: "docs/ already exists. How
   should docs-init proceed?" with options:
   - "Abort — leave docs/ untouched (Recommended)"
   - "Add missing pieces only — create only the missing standard folders and
     their template files; never overwrite or edit any existing file"
3. If AskUserQuestion fails or returns an empty answer, ask the same question
   in plain text and **end the turn** — wait for the user's reply. Never proceed
   on silence.
4. On "Add missing pieces only": do **not** copy by hand — that is a careful
   file operation, and it belongs in a script rather than in a prompt. Run:

   ```bash
   bash "$PLUGIN_ROOT/scripts/docs_scaffold.sh" --sync .
   ```

   It adds only what is absent and never overwrites, edits, or deletes. For a repo
   that just needs catching up with a newer docs-kit, `/docs-kit:docs-upgrade` is
   the whole job — it runs this and then regenerates the read models.

## Step 2 — Settle the profile, then scaffold (fresh repo path)

### 2a. Let the detector propose

```bash
python3 "$PLUGIN_ROOT/scripts/docs_detect.py" .
```

Read-only; it writes nothing. Two groups of lines matter here (the rest is for
Step 3):

- `owns-hint: <token> — <evidence>` — a proposal for `owns` in `.docs-kit.json`,
  which decides which folders this repo gets (STANDARD §9.1). Each hint states
  the evidence that produced it on the same line.
- `module-dir:` / `module-count:` — one directory per manifest found. More than
  one usually means more than one deployable, which is the question item 3 of
  Step 3 has to settle. Note it now; do not act on it yet.

### 2b. Ask — never scaffold a guess

Report the hints in Vietnamese **with their evidence**, then ask with
AskUserQuestion, `multiSelect: true`: "Repo này sở hữu những gì? (quyết định
`docs/` có bao nhiêu folder)". One option per token, pre-explained:

| Option | What it means | Folders it adds |
|---|---|---|
| `data` | repo này sở hữu bảng dữ liệu | — (ERD nằm trong `02_architecture/`) |
| `endpoints` | repo này phát ra một contract | `04_api/` |
| `screens` | repo này có route/màn hình | `60_fe-integration/` |
| `jobs` | repo này chạy worker/lịch chạy nền | — (component `[queue]`) |
| `deploys` | repo này được deploy và vận hành | `40_services/` `50_runbooks/` `70_deploy/` |

Mark the hinted tokens "(Recommended)". Nothing is preselected by the script —
the detector proposes, the user decides.

If AskUserQuestion fails or returns empty, ask in plain text and **end the turn**.
Do not fall back to "all 17 because it is safe": a profile nobody chose is the
state that rots, which is exactly what §9.1's three rules exist to prevent. Waiting
for an answer costs one turn; a wrong declaration costs every session after it.

### 2c. Scaffold the answer

```bash
bash "$PLUGIN_ROOT/scripts/docs_scaffold.sh" --owns data,endpoints,deploys .
```

Pass the confirmed tokens, comma-separated. `--owns ''` is correct for a repo that
owns nothing conditional (a library) — 11 core folders and no more. Omitting the
flag entirely is a different thing: it means "nobody declared", and yields all 17.

The script copies the folders that profile calls for (every folder ships a seed
file — templates are never empty), stamps today's date into `docs/92_audit/LOG.md`,
writes `.docs-kit.json` with the declaration, and prints the created file list
ending with `SCAFFOLD OK`. If it exits 3 (docs/ appeared meanwhile), go back to
Step 1. If `.docs-kit.json` already existed it is **not** touched — the script says
so and prints the `owns` key to add by hand; do that, or the declaration and the
tree disagree.

## Step 3 — Ground the Architecture in the real source (ASK FIRST)

A scaffold with an empty `components` list renders an empty sheet, and a
component list that is only a list of *names* tells a reader nothing they could
not have guessed from the directory listing. This step fills
`docs/02_architecture/architecture.md` from **the code that is actually in this
repo** — never from the project's name, its README's claims, or a framework's
conventional layout.

0. You already ran `docs_detect.py` in Step 2a — reuse that output, do not run it
   again. Report the rest of it in Vietnamese: language and version, services from
   docker-compose, notable dependencies. Nothing printed but `DETECT OK` means no
   manifest was found; say so plainly and move on, do not guess a stack from folder
   names.

   **Only `tech_stack:` may be filled from this report.** It states what a
   manifest declares, which is a fact. `components:` may not — a component's
   description is a claim about behaviour, and item 4 below is the bar it has
   to meet.

1. Ask with AskUserQuestion — question: "Đọc source của repo để điền
   Architecture (components, data flow, business flows)?" with options:
   - "Yes — đọc code rồi điền (Recommended)"
   - "No — để trống, tôi tự điền"
   Add a second question in the **same call** — one dialog, not two, because a
   trickle of dialogs is how a user stops reading them: "Điền `tech_stack:` từ
   những gì vừa nhận diện được?" with options "Yes — dùng bản nhận diện
   (Recommended)" and "No — để trống". Skip this second question when the
   detector found nothing.
   If AskUserQuestion fails or returns empty, ask in plain text and **end the
   turn**. Never fill layer 1 on silence.

2. On yes, read before you write. Identify entry points (`main`, server
   bootstrap, route tables, job registrations, migrations, `docker-compose`,
   deployment manifests), then follow the calls outward. Read enough of each
   component to state what it *is* — not what its folder is called.

3. **Decide how many Architecture documents this repo needs, before writing any.**
   `02_architecture/` is a folder. One deployable → keep `architecture.md`. Several
   (a monorepo of services, or one repo that ships more than one runnable thing) →
   one document per service, named after it: `orders.md`, `billing.md`. Each covers
   **only what that service owns**. `module-count:` from Step 2a is evidence, not
   the answer — two manifests can be one deployable plus its build tooling.

   Placement, so no fact is written twice (STANDARD §4): a component goes in the
   service that contains it; a table in the service that owns the writes; an edge
   `a -> b` in **`a`, the caller** — a dependency belongs to the thing that has it;
   the contract behind it in `b`. Component names must be unique across the folder,
   because `data_flow` resolves components by name.

   The scaffold ships a single `architecture.md`. Splitting means renaming it and
   adding siblings — say what you are doing and why before you do it.

4. Write `components`, one flat line each:
   `name [kind] `path/in/repo` — what it is, one sentence`. Rules:
   - the backticked path must be a path that **exists in this repo** — the
     reader will open it;
   - the description is a claim about behaviour you read (what it owns, what
     invariant it holds, what it decides), not a restatement of the name.
     "auth — handles auth" is a failure; "auth `src/auth/` — cấp JWT 15 phút,
     refresh token nằm ở bảng `sessions`" is the bar;
   - `[kind]`: `db` datastore · `queue` worker/queue · `ui` interface ·
     omitted for a service.
   Longer explanation goes in a `### <name>` body section, which the rendered
   card picks up.

5. Write `data_flow`, one edge per line, from real call sites and real
   queue/topic names: `a -> b : what moves`, `~>` when the caller does not wait.
   Only edges you can point at in the code.

6. Write the **business flows** — one ```` ```flow ```` block per scenario, in the
   body of the product doc it belongs to (or of architecture for system-level
   ones). Pick the scenarios a newcomer would ask about first: the main
   write path, the main read path, and whatever the money or the data integrity
   depends on. Each block: `title:`, `trigger:`, `code:` (where to read),
   ordered steps, `outcome:`. Participant names must match `components` so the
   figure picks up their icons. See STANDARD §10.

7. Write the **data model** — one ```` ```erd ```` block per architecture doc,
   holding the tables **that doc's service owns**, from the migrations or schema
   files that are actually in this repo.
   `table:` opens an entity, one column per line; a `fk -> other.id` flag is
   what draws a relationship, and cardinality is derived from it — never write
   cardinality by hand. Only tables and columns you read. See STANDARD §10.

8. Write the **types** — one ```` ```class ```` block per architecture doc,
   for the contract that matters most in that service: the interface with more than
   one implementation, the one a constraint depends on. `interface:` / `class:`
   open a type, `implements` and `extends` are relation lines, a field whose
   type names another declared type draws its own edge. Do not transcribe the
   whole package — pick the boundary a newcomer needs.

8.5 Write the **API contracts** into `docs/04_api/` — one file per service that
   publishes one. Skip this item entirely when the folder is not there: this repo
   did not declare `owns: endpoints` in Step 2b, and creating the folder anyway
   would route around the answer the user gave. One file per service publishing a
   contract; `service:` must name a component you just declared — that is the
   only join between the two folders and the validator enforces it. One
   ```` ```api ```` block per contract: `GET /orders/{id} -> Order — chú thích`,
   `event order.paid -> OrderPaid`.

   **Write the boundary, not the schema.** Status codes, field types and payload
   shapes belong to whatever generates them (OpenAPI, proto, the route table) — a
   hand-copy is stale within a sprint. What belongs here is which operations exist,
   what each means, and what the service deliberately does not expose. Only
   operations you read in the route table or the proto file.

9. Write the **business logic** into `docs/03_business-logic/` when the code has
   any: one ```` ```flowchart ```` per branching rule (`decide: node — câu hỏi?`
   makes a branch point) and one ```` ```state ```` per entity lifecycle
   (`initial:` / `final:` name real states). Each file needs `domain:` and
   `amended_by:` in its frontmatter. A rule that lives only in people's heads is
   exactly what this folder is for — but only write the ones you read in the
   code.

10. Set `verified_at:` in the Architecture (and Business logic) frontmatter to the
   current rev — you just read that code, so record when:

   ```bash
   git rev-parse --short HEAD
   ```

   From then on the validator reports when those files move on (`NOTE [stale]`),
   which is what turns re-verification from "whenever someone remembers" into
   "when something actually changed". Leave it empty if the repo has no commit yet.

11. State your confidence in the report. Anything inferred rather than read —
   say so, and leave it out rather than guess. An architecture doc that is
   confidently wrong is worse than an empty one.

## Step 4 — Self-check

Run:

```bash
bash "$PLUGIN_ROOT/scripts/docs_validate.sh" docs
```

A fresh scaffold must pass clean (the shipped `-000` example chain is
self-consistent by design). If it does not, report the raw FAIL lines to the
user as a plugin bug — do not hand-patch the generated files silently.

Then generate the HTML views (deterministic, read model — see STANDARD.md §10):

```bash
bash "$PLUGIN_ROOT/scripts/docs_render.sh" "$(pwd)"
```

This writes `docs/index.html` (menu, beside README.md), `docs/current.html`,
`docs/changes.html`, and `docs/INDEX.md`.

`INDEX.md` is the read model **for agents** — one line per document, so a skill can
find the ids it needs without globbing a folder (STANDARD §10). If the script exits 3
(`python3` missing), report that both read models were skipped: the HTML is cosmetic,
but a missing `INDEX.md` means `brief` and `docs-sync` fall back to reading whole
folders. Not fatal, worth saying out loud.

## Step 5 — Wire the rules into CLAUDE.md (ASK FIRST — ALWAYS)

The snippet lives at `$PLUGIN_ROOT/templates/claude-md-snippet.md` (trigger
table, "only Decision amends Architecture", the lane test, pointer to
`docs/README.md`). It is fenced by `<!-- docs-kit:start -->` /
`<!-- docs-kit:end -->` markers.

**Never write to CLAUDE.md without explicit consent — no exceptions.**

1. Ask with AskUserQuestion — question: "Append the docs-kit rules block to this
   repo's CLAUDE.md so agents follow the docs triggers?" with options:
   - "Yes — append to CLAUDE.md (Recommended)" (creates CLAUDE.md if absent)
   - "No — skip; I'll wire it myself"
2. If AskUserQuestion fails or returns an empty answer, ask the same question in
   plain text and **end the turn** — write only after the user answers yes.
3. On yes:
   - CLAUDE.md absent → create it containing the snippet.
   - CLAUDE.md present without docs-kit markers → append the snippet at the end,
     separated by one blank line. Change nothing else in the file.
   - Markers already present → replace only the content between the markers with
     the current snippet; report that it was refreshed.

## Step 6 — Report

Summarize: the profile the user chose and what it left out, folders/files created,
validation result, CLAUDE.md action taken (or skipped and why), and next steps —

- The profile is a declaration, not a guess, and it can change. A repo that grows
  an API adds `endpoints` to `.docs-kit.json` and runs `/docs-kit:docs-upgrade` to
  get `04_api/`. Nothing is ever removed on the way back.

- Read `docs/README.md` (30 seconds); open `docs/index.html` for the generated
  visual map (regenerate anytime with `/docs-kit:docs-render`).
- The `-000` files are a worked example chain; delete all four together or keep
  them as a format reference. Real IDs start at `001`.
- `/docs-kit:docs-sync` reconciles docs after a working session;
  `/docs-kit:docs-check` validates structure anytime.
- `docs/99_feedback/` is the one folder that is not about this product: when
  docs-kit or crew gets something wrong here, one file goes in there
  (`docs_feedback.sh new <slug>`) and that file is a prompt the maintainer can
  act on as-is. Read `docs/99_feedback/README.md` for the four cases that qualify.
- The plugin's hooks now warn (never block) on direct `docs/02_architecture/` or `docs/03_business-logic/`
  edits and on sensitive-zone changes without an Issue/Decision. Sensitive
  patterns are configurable via `.docs-kit.json` (see STANDARD.md §9).
