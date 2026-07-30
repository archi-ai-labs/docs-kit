---
id: PROPOSAL-000
issue_ref: ISSUE-000
problem: "Logs are unstructured plain text; cross-service debugging requires fragile grep chains"
proposed: "Adopt JSON-lines logging with a shared field set (ts, level, service, trace_id, msg)"
impact: "none"
---

# PROPOSAL-000 — Example: structured logging format

> Part of the `-000` worked example chain. See `20_issues/ISSUE-000-example.md`.

## Problem

Restate the problem from the Issue with any new evidence gathered while exploring.

## Alternatives considered

1. **JSON-lines with a shared field set (proposed)** — machine-parseable everywhere;
   trade-off: slightly noisier for humans reading raw logs.
2. **logfmt (`key=value`)** — human-friendlier; trade-off: weaker nested-data support,
   fewer off-the-shelf parsers in our stack.
3. **Keep plain text + better conventions** — zero migration cost; trade-off: does not
   solve machine parsing, the original problem remains.

## Proposed option

Option 1. Roll out via a shared logging helper; services migrate call sites
incrementally behind the same interface.

## Impact on Architecture / Roadmap

None — no component boundary or roadmap change (`impact: none` above). If a
proposal does affect them, describe exactly what would be amended.
