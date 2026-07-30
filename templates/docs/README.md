# docs/ — three-layer documentation

Scaffolded by docs-kit. Full standard: docs-kit `STANDARD.md`. Read this file first — 30 seconds.

## 1 · Layers

| Layer | Folders | Nature | Edit rule |
|---|---|---|---|
| 1 · Foundation | `00_roadmap` `01_products` `02_architecture` | State | Architecture changes **only** via an approved Decision (`amended_by`) |
| 2 · Change | `20_issues` `21_proposals` `22_decisions` `23_backlog` | Process, traceable | Follow the flow below |
| 3 · Reference | `30_conventions` `40_services` `50_runbooks` `60_fe-integration` `70_deploy` `93_qa` | Operational reference | Edit directly, no Decision needed |
| Oversight | `92_audit` | Append-only audit log | Append lines only, never rewrite |

## 2 · Flow

```
Issue (exploring → open)
  ├─ FAST lane ──────────────────────────────► Backlog (source_ref = Issue)
  └─ FULL lane ──► Proposal ──► Decision ────► Backlog (source_ref = Decision)
Decision approved   ⇒ amend 02_architecture in the SAME session (amended_by entry)
Backlog item done   ⇒ status: done + append one line to 92_audit/
Review (periodic)   ⇒ read-only over layers 1–2; findings appended to 92_audit/
```

## 3 · Lane test — two questions, any "yes" ⇒ FULL lane

1. Does this change modify the Architecture doc?
2. If it turns out wrong, would reverting take more than 1 day?

## 4 · Folders

| # | Folder | Purpose (one line) |
|---|---|---|
| 00 | `00_roadmap` | Where the product is heading: now / next / later |
| 01 | `01_products` | What each product is, for whom, and what success means |
| 02 | `02_architecture` | Components, data flow, stack, constraints — amended only via Decision |
| 20 | `20_issues` | Anything worth doing enters here first (research starts as `exploring`) |
| 21 | `21_proposals` | Full-lane options with alternatives + trade-offs |
| 22 | `22_decisions` | Approved / rejected calls, by whom, and why |
| 23 | `23_backlog` | Executable work items with `source_ref` traceability |
| 30 | `30_conventions` | Coding / naming / process conventions |
| 40 | `40_services` | Service reference: what runs where, owned by whom |
| 50 | `50_runbooks` | Step-by-step operational procedures |
| 60 | `60_fe-integration` | Contracts and notes for frontend integration |
| 70 | `70_deploy` | How to ship: environments, pipeline, rollback |
| 92 | `92_audit` | Append-only audit log — the traceability lookup |
| 93 | `93_qa` | Test strategy, QA checklists, known gaps |

## 5 · Traceability

`92_audit/` is where you look up *what happened, under which Decision/Backlog, and
what deviated*. Append-only — validated against git history.

IDs (`ISSUE-`, `PROPOSAL-`, `DECISION-`, `BACKLOG-` + 3-digit number) live in
frontmatter `id:`; every `*_ref:` points to an ID, **never to a file name**.
The shipped `*-000` files are a worked example chain — delete all four together
or keep them as a format reference. Real IDs start at `001`.

Validate structure anytime: `/docs-kit:docs-check` · Reconcile after a work
session: `/docs-kit:docs-sync`
