# docs-kit

Three-layer docs workflow as an installable Claude Code plugin: scaffold the
structure, keep it in sync with what sessions actually do, and enforce the rules
with deterministic warn-only hooks.

```
LAYER 1 — FOUNDATION   Products → Roadmap → Architecture      (state; only Decisions amend)
LAYER 2 — CHANGE       Issue → [Proposal → Decision] → Backlog (process; traceable)
LAYER 3 — REFERENCE    Conventions/Services/Runbooks/Deploy/FE/QA (edit directly)
OVERSIGHT              92_audit — append-only audit log
```

The full model lives in [STANDARD.md](STANDARD.md) — the source of truth every
skill, hook, and template conforms to.

## Install

```
/plugin install docs-kit@archimonde12
```

## Use

| Command | What it does |
|---|---|
| `/docs-kit:docs-init` | Scaffold 14 folders + templates + `docs/README.md` into the repo; optionally (always asks first) wire the rules into `CLAUDE.md`. Refuses to touch an existing `docs/`. |
| `/docs-kit:docs-sync` | End-of-session reconcile: backlog statuses, audit entries, retroactive Issues, pending Architecture amendments. |
| `/docs-kit:docs-check` | Read-only: run `scripts/docs_validate.sh` and explain each failure. Never fixes. |

## Enforcement (warn-only, no LLM in hooks)

- **PostToolUse** (Edit/Write): editing `docs/02_architecture/` prints a reminder
  that Architecture is amended only via the Decision workflow.
- **Stop**: if the session edited sensitive paths (default `**/schema/**`,
  `**/api/**`, `**/migrations/**`; override via `.docs-kit.json` in the repo)
  without creating or referencing any Issue/Decision, it reminds you to run
  `/docs-kit:docs-sync`.

Warn-only by design: the rules haven't been battle-tested yet, and a false
positive that blocks teaches people to disable hooks. Both hooks are silent in
repos without a `docs/` skeleton.

## Layout

```
docs-kit/
├── .claude-plugin/plugin.json
├── STANDARD.md              # source of truth for the model
├── skills/                  # docs-init (entry point), docs-sync, docs-check
├── commands/                # thin wrappers → /docs-kit:docs-*
├── hooks/hooks.json         # 2 deterministic warn-only hooks
├── scripts/                 # docs_validate.sh, docs_scaffold.sh, hook workers
└── templates/               # the 14-folder docs tree + CLAUDE.md snippet
```
