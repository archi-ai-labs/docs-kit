<!-- docs-kit:start (managed by /docs-kit:docs-init — edit between markers only via docs-kit) -->
## Documentation rules (docs-kit)

This repo uses the three-layer docs model in `docs/` — read `docs/README.md` first (30 seconds).

**Hard rule:** only the Decision workflow may change `docs/02_architecture/` — every
amendment appends an `amended_by` entry citing the approving Decision, in the same
session it is approved.

**Lane test** — two questions, any "yes" → full lane (Issue → Proposal → Decision →
Backlog); both "no" → fast lane (Issue → Backlog):
1. Does this change modify the Architecture doc?
2. If it turns out wrong, would reverting take more than 1 day?

**Mandatory triggers:**

| Session event | Required docs action |
|---|---|
| Code change touches a schema, API contract, or component boundary | A Decision must already exist. If none: create an Issue, stop, ask the user. |
| A Backlog item is completed | Set its `status: done` + append one line to `docs/92_audit/`. |
| A Decision is approved | Amend `docs/02_architecture/` in the SAME session. |
| Starting work that is not in the Backlog | Create an Issue before writing code. |

End sessions that changed code with `/docs-kit:docs-sync`; validate structure with `/docs-kit:docs-check`.
<!-- docs-kit:end -->
