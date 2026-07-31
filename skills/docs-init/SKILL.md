---
name: docs-init
description: The main entry point. Scaffold the three-layer docs structure into this repo — 15 folders, templates, docs/README.md — and optionally wire the rules into CLAUDE.md.
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
1. Report the current state: which of the 15 standard folders are present /
   missing (the scaffold script prints exactly this if you run it — it refuses
   with exit 3 and touches nothing), plus any non-standard entries.
2. Ask the user with AskUserQuestion — question: "docs/ already exists. How
   should docs-init proceed?" with options:
   - "Abort — leave docs/ untouched (Recommended)"
   - "Add missing pieces only — create only the missing standard folders and
     their template files; never overwrite or edit any existing file"
3. If AskUserQuestion fails or returns an empty answer, ask the same question
   in plain text and **end the turn** — wait for the user's reply. Never proceed
   on silence.
4. On "Add missing pieces only": copy from `$PLUGIN_ROOT/templates/docs/` only
   the folders/files that do not exist yet (`cp -Rn` semantics; check each path
   first). Never overwrite an existing file.

## Step 2 — Scaffold (fresh repo path)

Run:

```bash
bash "$PLUGIN_ROOT/scripts/docs_scaffold.sh" .
```

The script copies the 15-folder template tree to `./docs/` (every folder ships a
seed file — templates are never empty), stamps today's date into
`docs/92_audit/LOG.md`, and prints the created file list ending with
`SCAFFOLD OK`. If it exits 3 (docs/ appeared meanwhile), go back to Step 1.

## Step 3 — Ground the Architecture in the real source (ASK FIRST)

A scaffold with an empty `components` list renders an empty sheet, and a
component list that is only a list of *names* tells a reader nothing they could
not have guessed from the directory listing. This step fills
`docs/02_architecture/architecture.md` from **the code that is actually in this
repo** — never from the project's name, its README's claims, or a framework's
conventional layout.

0. First, see what this repo is built with:

   ```bash
   python3 "$PLUGIN_ROOT/scripts/docs_detect.py" .
   ```

   It is read-only and writes nothing. Report the findings in Vietnamese —
   language and version, services from docker-compose, notable dependencies.
   Nothing printed but `DETECT OK` means no manifest was found; say so plainly
   and move on, do not guess a stack from folder names.

   **Only `tech_stack:` may be filled from this report.** It states what a
   manifest declares, which is a fact. `components:` may not — a component's
   description is a claim about behaviour, and item 3 below is the bar it has
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

3. Write `components`, one flat line each:
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

4. Write `data_flow`, one edge per line, from real call sites and real
   queue/topic names: `a -> b : what moves`, `~>` when the caller does not wait.
   Only edges you can point at in the code.

5. Write the **business flows** — one ```` ```flow ```` block per scenario, in the
   body of the product doc it belongs to (or of architecture for system-level
   ones). Pick the scenarios a newcomer would ask about first: the main
   write path, the main read path, and whatever the money or the data integrity
   depends on. Each block: `title:`, `trigger:`, `code:` (where to read),
   ordered steps, `outcome:`. Participant names must match `components` so the
   figure picks up their icons. See STANDARD §10.

6. Write the **data model** — one ```` ```erd ```` block in the architecture
   body, from the migrations or schema files that are actually in this repo.
   `table:` opens an entity, one column per line; a `fk -> other.id` flag is
   what draws a relationship, and cardinality is derived from it — never write
   cardinality by hand. Only tables and columns you read. See STANDARD §10.

7. Write the **types** — one ```` ```class ```` block in the architecture body,
   for the contract that matters most in this repo: the interface with more than
   one implementation, the one a constraint depends on. `interface:` / `class:`
   open a type, `implements` and `extends` are relation lines, a field whose
   type names another declared type draws its own edge. Do not transcribe the
   whole package — pick the boundary a newcomer needs.

8. Write the **business logic** into `docs/03_business-logic/` when the code has
   any: one ```` ```flowchart ```` per branching rule (`decide: node — câu hỏi?`
   makes a branch point) and one ```` ```state ```` per entity lifecycle
   (`initial:` / `final:` name real states). Each file needs `domain:` and
   `amended_by:` in its frontmatter. A rule that lives only in people's heads is
   exactly what this folder is for — but only write the ones you read in the
   code.

9. State your confidence in the report. Anything inferred rather than read —
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
and `docs/changes.html`. If the script exits 3 (`python3` missing), report that
the HTML views were skipped and continue — it is not fatal.

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

Summarize: folders/files created, validation result, CLAUDE.md action taken
(or skipped and why), and next steps —

- Read `docs/README.md` (30 seconds); open `docs/index.html` for the generated
  visual map (regenerate anytime with `/docs-kit:docs-render`).
- The `-000` files are a worked example chain; delete all four together or keep
  them as a format reference. Real IDs start at `001`.
- `/docs-kit:docs-sync` reconciles docs after a working session;
  `/docs-kit:docs-check` validates structure anytime.
- The plugin's hooks now warn (never block) on direct `docs/02_architecture/` or `docs/03_business-logic/`
  edits and on sensitive-zone changes without an Issue/Decision. Sensitive
  patterns are configurable via `.docs-kit.json` (see STANDARD.md §9).
