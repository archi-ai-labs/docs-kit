#!/usr/bin/env python3
"""Build the fictional 'orderhub' docs tree used for visual checks + design samples.

Usage: make-fixture.py <dir>   — writes <dir>/docs/... and nothing else.

The fixture deliberately exercises every branch of the renderer: both lanes,
an amended architecture (two revisions), all board columns including archived
and not-doing, a recorded deviation, and an empty Layer-3 folder. Driven by
../make-samples.sh, which renders it and writes design/sample-*.html.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
docs = root / "docs"

FILES = {}

FILES["00_roadmap/roadmap.md"] = """# Roadmap

> Layer 1 — Foundation. Keep this aligned with approved Decisions.

## Now

- BACKLOG-004 Webhook retry with exponential backoff
- BACKLOG-005 Idempotent order intake keys

## Next

- Refund flow v2
- Per-merchant rate limits

## Later / someday

- Multi-currency support (ISSUE-005)
- Merchant sandbox mode

## Explicitly not doing

- Building our own PSP (DECISION-002)
"""

FILES["01_products/orderhub-api.md"] = """---
name: "OrderHub API"
users: "Merchant developers integrating order intake — backend-savvy, REST/gRPC fluent"
problem: "Order intake is fragmented across three channels with no single source of order state"
scope_in: [Order intake API, Payment capture via adapter, Status webhooks]
scope_out: [Inventory management, Shipping labels]
success_metric: "99% of orders acknowledged in < 2s"
---

# OrderHub API

## What it is

OrderHub API is the single entry point for order creation and lifecycle tracking.
Merchants integrate once and receive a consistent state machine regardless of the
sales channel the order originated from.
"""

FILES["01_products/merchant-dashboard.md"] = """---
name: "Merchant Dashboard"
users: "Merchant operations staff — non-technical, browser only"
problem: "No single view of an order's lifecycle when a payment fails"
scope_in: [Live order feed, Refund actions]
scope_out: [Analytics warehouse]
success_metric: "Time-to-first-action on a failed payment < 5 min"
---

# Merchant Dashboard

## What it is

A read-mostly console over the same API, focused on time-to-first-action when
something goes wrong with an order.
"""

FILES["02_architecture/architecture.md"] = """---
components:
  - "api-gateway — Authn, per-merchant rate limits, request shaping"
  - "order-service — Order lifecycle state machine, single writer of order state"
  - "payment-adapter — The only egress to external PSPs; normalizes capture/refund"
  - "postgres [db] — Orders + outbox tables, source of durable state"
  - "worker [queue] — Outbox consumer: webhook delivery, retries, dead-letter"
data_flow:
  - "client -> api-gateway -> order-service"
  - "order-service -> payment-adapter : capture"
  - "payment-adapter -> PSP"
  - "order-service -> postgres"
  - "postgres ~> worker : outbox"
  - "worker -> merchant webhook"
tech_stack: [Go 1.22, PostgreSQL 16, Redis 7, gRPC, Terraform]
constraints:
  - "payment-adapter is the only component allowed to call external PSPs"
  - "All state changes go through the outbox pattern — no dual writes"
  - "p99 order intake latency < 300 ms"
  - "Single region until multi-currency lands"
amended_by:
  - "2026-06-14 DECISION-001 Introduce outbox table + delivery worker"
  - "2026-07-02 DECISION-002 External PSP calls only via payment-adapter"
---

# Architecture

## Components

See the frontmatter list — one entry per component.

## Data flow

The frontmatter edges are the authoritative flow description.
"""

def issue(n, desc, why, lane, status):
    return """---
id: ISSUE-%03d
description: "%s"
why: "%s"
lane: %s
status: %s
---

# ISSUE-%03d — %s
""" % (n, desc, why, lane, status, n, desc)

FILES["20_issues/ISSUE-001-gateway-502.md"] = issue(1, "Gateway 502 flapping (runbook, not a change)", "Ops noise, belongs in runbooks", "fast", "archived")
FILES["20_issues/ISSUE-002-webhooks-lost.md"] = issue(2, "Webhooks lost when service crashes mid-send", "Merchants miss order updates silently", "full", "promoted")
FILES["20_issues/ISSUE-003-psp-direct.md"] = issue(3, "Services call PSPs directly, bypassing the adapter", "Breaks the single-egress constraint", "full", "promoted")
FILES["20_issues/ISSUE-004-retry-storm.md"] = issue(4, "Webhook retry storm duplicates deliveries", "Hotfixed in prod before an Issue existed", "fast", "promoted")
FILES["20_issues/ISSUE-005-multi-currency.md"] = issue(5, "Multi-currency support", "Requested by two enterprise merchants", "full", "exploring")
FILES["20_issues/ISSUE-006-refund-bypass.md"] = issue(6, "Refund flow bypasses order state machine", "Refunds can contradict order state", "full", "open")

FILES["21_proposals/PROPOSAL-001-outbox.md"] = """---
id: PROPOSAL-001
issue_ref: ISSUE-002
problem: "Webhooks are sent inline; a crash between DB write and send loses them"
proposed: "Outbox table + delivery worker for at-least-once webhooks"
impact: "Architecture change: new worker component and outbox table; roadmap unchanged"
---

# PROPOSAL-001 — Outbox + delivery worker

## Alternatives considered

1. **Inline retries with backoff** — simplest, but a crash still loses the webhook.
2. **Message broker (Redis streams)** — new infra to operate for one use case.
3. **Outbox + worker (chosen)** — at-least-once with only postgres + one consumer.
"""

FILES["21_proposals/PROPOSAL-002-psp-adapter.md"] = """---
id: PROPOSAL-002
issue_ref: ISSUE-003
problem: "Two services call PSP SDKs directly, duplicating retry and error logic"
proposed: "Route all PSP traffic through payment-adapter; forbid direct calls"
impact: "Architecture change: payment-adapter becomes the single PSP egress"
---

# PROPOSAL-002 — Single PSP egress

## Alternatives considered

1. **Shared SDK wrapper library** — still N callers, N configs to rotate.
2. **Per-service allowlists** — policy without enforcement point.
3. **Adapter as single egress (chosen)** — one place for retries, keys, audit.
"""

def decision(n, pref, outcome, reason, amendment):
    return """---
id: DECISION-%03d
proposal_ref: PROPOSAL-%03d
outcome: %s
reason: "%s"
decided_by: hoan
architecture_amendment: "%s"
---

# DECISION-%03d
""" % (n, pref, outcome, reason, amendment, n)

FILES["22_decisions/DECISION-001-outbox.md"] = decision(1, 1, "approved", "At-least-once delivery with minimal new infra", "Introduce outbox table + delivery worker")
FILES["22_decisions/DECISION-002-psp-adapter.md"] = decision(2, 2, "approved", "Single egress point for keys, retries, and audit", "External PSP calls only via payment-adapter")

def backlog(n, desc, src, status):
    return """---
id: BACKLOG-%03d
description: "%s"
source_ref: %s
status: %s
---

# BACKLOG-%03d — %s
""" % (n, desc, src, status, n, desc)

FILES["23_backlog/BACKLOG-001-outbox-migration.md"] = backlog(1, "Outbox table migration", "DECISION-001", "done")
FILES["23_backlog/BACKLOG-002-delivery-worker.md"] = backlog(2, "Delivery worker + dead-letter", "DECISION-001", "done")
FILES["23_backlog/BACKLOG-003-psp-cutover.md"] = backlog(3, "PSP adapter cutover", "DECISION-002", "done")
FILES["23_backlog/BACKLOG-004-retry-backoff.md"] = backlog(4, "Webhook retry with exponential backoff", "ISSUE-004", "in-progress")
FILES["23_backlog/BACKLOG-005-idempotent-intake.md"] = backlog(5, "Idempotent order intake keys", "DECISION-001", "open")

FILES["92_audit/LOG.md"] = """# Audit log

> Append-only. Format: `YYYY-MM-DD | what happened | ref | deviation ("-" if none) | why`

2026-05-02 | docs skeleton scaffolded | - | - | -
2026-05-10 | ISSUE-001 archived to runbooks | ISSUE-001 | - | ops noise, not a change
2026-05-28 | ISSUE-002 opened | ISSUE-002 | - | -
2026-06-05 | PROPOSAL-001 drafted | PROPOSAL-001 | - | -
2026-06-14 | DECISION-001 approved, architecture REV A | DECISION-001 | - | -
2026-06-16 | BACKLOG-001 done — outbox migration | BACKLOG-001 | - | -
2026-06-20 | BACKLOG-002 done — delivery worker live | BACKLOG-002 | - | -
2026-06-24 | ISSUE-003 opened | ISSUE-003 | - | -
2026-06-30 | PROPOSAL-002 drafted | PROPOSAL-002 | - | -
2026-07-02 | DECISION-002 approved, architecture REV B | DECISION-002 | - | -
2026-07-15 | Hotfix pushed before Issue existed | ISSUE-004 | retroactive Issue | prod webhook storm
2026-07-28 | BACKLOG-003 done — PSP adapter cutover | BACKLOG-003 | - | -
"""

FILES["30_conventions/coding-style.md"] = "# Coding style\n\nGo fmt, table-driven tests.\n"
FILES["30_conventions/review-rules.md"] = "# Review rules\n\nTwo approvals on schema changes.\n"
FILES["40_services/order-service.md"] = "# order-service\n\nOwns order state.\n"
FILES["50_runbooks/gateway-502.md"] = "# Gateway 502\n\nCheck upstream health.\n"
FILES["50_runbooks/psp-outage.md"] = "# PSP outage\n\nQueue captures, notify merchants.\n"
FILES["50_runbooks/webhook-storm.md"] = "# Webhook storm\n\nPause worker, drain dead-letter.\n"
FILES["70_deploy/environments.md"] = "# Environments\n\nstaging, prod (single region).\n"
FILES["93_qa/test-matrix.md"] = "# Test matrix\n\nIntake, capture, refund, webhook.\n"
FILES["README.md"] = "# docs\n\nThree-layer docs. 30-second guide lives here in the real scaffold.\n"

for folder in ["60_fe-integration"]:
    (docs / folder).mkdir(parents=True, exist_ok=True)

for rel, content in FILES.items():
    p = docs / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

print("fixture ready at", root)
