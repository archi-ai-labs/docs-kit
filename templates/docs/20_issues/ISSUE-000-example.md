---
id: ISSUE-000
description: "EXAMPLE — adopt a structured logging format across services"
why: "Grep-based debugging across plain-text logs is slow and error-prone; structured fields make incidents traceable"
lane: full
status: promoted
---

# ISSUE-000 — Example: adopt a structured logging format

> **Worked example** shipped by docs-init. It demonstrates the full-lane chain:
> ISSUE-000 → PROPOSAL-000 → DECISION-000 → BACKLOG-000 (+ one line in `92_audit/`).
> Delete all four `-000` files together (they reference each other), or keep them
> as a format reference. Real Issues start at `ISSUE-001`.

## Notes

Lane test: it does **not** modify the Architecture doc (question 1 = no), but
rolling the format back across all services would take more than a day
(question 2 = yes) → **full lane**.

An Issue starts as `status: exploring` while it is raw research, becomes `open`
when it is a real candidate, `promoted` once a Proposal exists (full lane) or a
Backlog item exists (fast lane), and `archived` when dropped or superseded.
