# Audit log — append-only

Review is READ-ONLY over layers 1–2: findings land here and only here.
One line per event, **appended at the end**. Never insert, edit, or delete
existing lines — `docs-check` validates this file against git HEAD.

Format: `YYYY-MM-DD | what happened | ref | deviation from Decision/Backlog ("-" if none) | why`

---

{{DOCS_KIT_DATE}} | docs skeleton initialized by docs-kit | - | - | baseline entry
{{DOCS_KIT_DATE}} | BACKLOG-000 completed (worked example) | BACKLOG-000 (DECISION-000) | - | demonstrates the completion trigger
