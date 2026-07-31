#!/usr/bin/env python3
"""Build the fictional 'orderhub' docs tree used for visual checks + design samples.

Usage: make-fixture.py <dir>   — writes <dir>/docs/... and nothing else.

The fixture deliberately exercises every branch of the renderer: both lanes,
an amended architecture (two revisions), all board columns including archived
and not-doing, a recorded deviation, and an empty Layer-3 folder. Driven by
../make-samples.sh, which renders it and writes design/sample-*.html.

Language follows STANDARD §11: structure and terms in English, explanation in
Vietnamese — the fixture has to look like real output, not a translation test.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
docs = root / "docs"

FILES = {}

FILES["00_roadmap/roadmap.md"] = """# Roadmap

> Layer 1 — Foundation. Giữ đồng bộ với các Decision đã duyệt.

## Now

- BACKLOG-004 Retry webhook với backoff luỹ thừa
- BACKLOG-005 Khoá idempotent cho luồng nhận đơn

## Next

- Luồng hoàn tiền v2
- Giới hạn tần suất theo từng merchant

## Later / someday

- Hỗ trợ đa tiền tệ (ISSUE-005)
- Chế độ sandbox cho merchant

## Explicitly not doing

- Tự xây PSP riêng (DECISION-002)
"""

FILES["01_products/orderhub-api.md"] = """---
name: "OrderHub API"
users: "Lập trình viên phía merchant tích hợp luồng nhận đơn — rành backend, quen REST/gRPC"
problem: "Luồng nhận đơn nằm rải trên ba kênh, không có nguồn duy nhất cho trạng thái đơn"
scope_in: [API nhận đơn, Capture thanh toán qua adapter, Webhook trạng thái]
scope_out: [Quản lý kho, In nhãn vận chuyển]
success_metric: "99% đơn được xác nhận trong < 2s"
---

# OrderHub API

## What it is

OrderHub API là cửa vào duy nhất để tạo đơn và theo dõi vòng đời đơn. Merchant
tích hợp một lần và nhận về cùng một state machine, bất kể đơn đến từ kênh bán nào.

## Business flows

```flow
title: Nhận một đơn mới
trigger: POST /v1/orders kèm Idempotency-Key của merchant
code: internal/order/create.go
api-gateway -> order-service : HMAC hợp lệ, đã qua rate limit
order-service -> order-service : từ chối nếu Idempotency-Key đã dùng
order-service -> payment-adapter : capture số tiền của đơn
payment-adapter -> order-service : capture ok kèm mã giao dịch PSP
order-service -> postgres : ghi orders + outbox trong MỘT transaction
postgres ~> worker : outbox có dòng mới
worker ~> api-gateway : gửi webhook order.confirmed
outcome: Đơn ở trạng thái confirmed, tiền đã capture, webhook đã xếp hàng
```

```flow
title: Hoàn tiền một đơn đã capture
trigger: Nhân viên vận hành bấm Refund trên Merchant Dashboard
code: internal/order/refund.go
api-gateway -> order-service : refund cho order id
order-service -> order-service : chỉ cho refund khi đang ở confirmed
order-service -> payment-adapter : refund theo mã giao dịch PSP
order-service -> postgres : ghi trạng thái refunded + outbox
postgres ~> worker : gửi webhook order.refunded
outcome: Đơn ở trạng thái refunded; lệch tiền sẽ hiện ở Reconciliation cuối ngày
```
"""

FILES["01_products/merchant-dashboard.md"] = """---
name: "Merchant Dashboard"
users: "Nhân viên vận hành phía merchant — không rành kỹ thuật, chỉ dùng trình duyệt"
problem: "Không có chỗ nào nhìn được trọn vòng đời một đơn khi thanh toán lỗi"
scope_in: [Luồng đơn thời gian thực, Thao tác hoàn tiền]
scope_out: [Kho dữ liệu phân tích]
success_metric: "Thời gian tới thao tác đầu tiên khi thanh toán lỗi < 5 phút"
---

# Merchant Dashboard

## What it is

Một console chủ yếu để đọc, đặt trên cùng API đó, tập trung vào việc rút ngắn thời
gian tới thao tác đầu tiên khi một đơn có vấn đề.
"""

# Named in the same register as its two siblings, per STANDARD §11: product names
# are proper nouns, and one odd name out reads as a leak in the §1 sidebar list.
FILES["01_products/reconciliation.md"] = """---
name: "Reconciliation"
users: "Kế toán merchant — làm việc theo ngày, đối chiếu số liệu cuối phiên"
problem: "Số liệu giữa OrderHub và sao kê PSP lệch nhau mà không biết lệch ở đâu"
scope_in: [Đối chiếu theo ngày, Xuất báo cáo lệch]
scope_out: [Hạch toán kế toán, Xuất hoá đơn]
success_metric: "Mọi khoản lệch trong ngày được quy về một giao dịch cụ thể trong < 1 giờ"
---

# Reconciliation

## What it is

Đối chiếu từng giao dịch giữa trạng thái đơn của OrderHub và sao kê PSP, rồi chỉ
đúng giao dịch gây lệch thay vì báo một con số tổng.
"""

FILES["02_architecture/architecture.md"] = """---
components:
  - "api-gateway `cmd/gateway/` — Xác thực merchant bằng HMAC, giới hạn 200 req/s mỗi key, nắn request rồi chuyển tiếp"
  - "order-service `internal/order/` — Giữ state machine vòng đời đơn; nơi DUY NHẤT được ghi cột `orders.status`"
  - "payment-adapter `internal/psp/` — Lối ra duy nhất tới PSP ngoài; chuẩn hoá capture/refund về một interface, dịch mã lỗi PSP"
  - "postgres [db] `deploy/postgres/` — Bảng `orders` + `outbox` trong cùng một transaction; nguồn trạng thái bền vững"
  - "worker [queue] `cmd/worker/` — Consumer của outbox: gửi webhook, retry backoff luỹ thừa, dead-letter sau 12 lần"
data_flow:
  - "client -> api-gateway -> order-service"
  - "order-service -> payment-adapter : capture"
  - "payment-adapter -> PSP"
  - "PSP ~> payment-adapter : webhook kết quả"
  - "payment-adapter -> order-service : mã lỗi đã chuẩn hoá"
  - "order-service -> postgres"
  - "postgres ~> worker : outbox"
  - "worker -> merchant webhook"
  - "worker -> worker : retry backoff luỹ thừa"
tech_stack: [Go 1.22, PostgreSQL 16, Redis 7, gRPC, Terraform]
constraints:
  - "Chỉ payment-adapter được phép gọi PSP bên ngoài"
  - "Mọi thay đổi trạng thái đi qua outbox pattern — không ghi hai nơi"
  - "Độ trễ p99 khi nhận đơn < 300 ms"
  - "Chạy một region cho tới khi đa tiền tệ xong"
amended_by:
  - "2026-06-14 DECISION-001 Thêm bảng outbox + worker gửi webhook"
  - "2026-07-02 DECISION-002 Gọi PSP ngoài chỉ qua payment-adapter"
---

# Architecture

## Components

Xem danh sách trong frontmatter — mỗi component một dòng.

### order-service

Single-writer cho `orders.status`. Mọi chuyển trạng thái đi qua một transaction
duy nhất ghi đồng thời `orders` và `outbox`, nên không có cửa sổ nào mà đơn đã
đổi trạng thái còn webhook thì chưa được xếp hàng. Chuyển trạng thái không hợp lệ
bị từ chối ở tầng domain, không phải ở tầng HTTP.

### payment-adapter

Không giữ state. Mỗi lần capture mang theo idempotency key sinh từ order id, nên
PSP nhận lại cùng một key sẽ trả về kết quả cũ thay vì thu tiền hai lần.

## Data model

```erd
title: Lược đồ orderhub
code: internal/store/schema.sql

table: merchants
id           uuid         pk
name         text
hmac_key     text — khoá ký request, xoay vòng 90 ngày
created_at   timestamptz

table: orders
id                uuid    pk
merchant_id       uuid    fk -> merchants.id — merchant sở hữu đơn này
parent_order_id   uuid    fk -> orders.id null — đơn gốc khi tách kiện
status            text
total_cents       bigint
created_at        timestamptz

table: order_items
id         uuid     pk
order_id   uuid     fk -> orders.id
sku        text
qty        int
unit_cents bigint

table: refunds
id           uuid     pk
order_id     uuid     fk -> orders.id unique — mỗi đơn hoàn nhiều nhất một lần
amount_cents bigint
psp_ref      text

table: outbox
id          uuid          pk
order_id    uuid          fk -> orders.id
topic       text
payload     jsonb
sent_at     timestamptz null
```

## Types & contracts

```class
title: Lối ra PSP
code: internal/psp/

interface: PSPClient
+ Capture(orderID string, cents int64) (Receipt, error)
+ Refund(orderID string, cents int64) (Receipt, error)

class: BaseAdapter
- http       *http.Client
- timeout    time.Duration
+ do(req Request) (Response, error) — chỗ duy nhất đặt timeout và retry

class: StripeAdapter
extends BaseAdapter
implements PSPClient
- secret      string
- lastReceipt Receipt — biên lai của lần gọi gần nhất, dùng cho idempotency
+ Capture(orderID string, cents int64) (Receipt, error)
+ Refund(orderID string, cents int64) (Receipt, error)

class: SandboxAdapter
implements PSPClient
- fixtures map[string]Receipt
+ Capture(orderID string, cents int64) (Receipt, error)
+ Refund(orderID string, cents int64) (Receipt, error)

class: Receipt
+ PSPRef  string
+ Status  string
+ Cents   int64
```

## Data flow

Các cạnh khai trong frontmatter mới là mô tả luồng có thẩm quyền.
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

FILES["20_issues/ISSUE-001-gateway-502.md"] = issue(1, "Gateway 502 chập chờn (thuộc runbook, không phải thay đổi)", "Nhiễu vận hành, chỗ của nó là runbook", "fast", "archived")
FILES["20_issues/ISSUE-002-webhooks-lost.md"] = issue(2, "Mất webhook khi service chết giữa lúc đang gửi", "Merchant âm thầm lỡ cập nhật đơn", "full", "promoted")
FILES["20_issues/ISSUE-003-psp-direct.md"] = issue(3, "Service gọi thẳng PSP, đi vòng qua adapter", "Phá ràng buộc chỉ một lối ra", "full", "promoted")
FILES["20_issues/ISSUE-004-retry-storm.md"] = issue(4, "Bão retry webhook làm gửi trùng", "Đã hotfix trên prod trước khi có Issue", "fast", "promoted")
FILES["20_issues/ISSUE-005-multi-currency.md"] = issue(5, "Hỗ trợ đa tiền tệ", "Hai merchant lớn cùng yêu cầu", "full", "exploring")
FILES["20_issues/ISSUE-006-refund-bypass.md"] = issue(6, "Luồng hoàn tiền đi vòng qua state machine của đơn", "Hoàn tiền có thể mâu thuẫn với trạng thái đơn", "full", "open")

FILES["21_proposals/PROPOSAL-001-outbox.md"] = """---
id: PROPOSAL-001
issue_ref: ISSUE-002
problem: "Webhook đang gửi inline; chết giữa lúc ghi DB và lúc gửi là mất luôn"
proposed: "Bảng outbox + worker gửi, để webhook đạt at-least-once"
impact: "Đổi Architecture: thêm component worker và bảng outbox; roadmap không đổi"
---

# PROPOSAL-001 — Outbox + delivery worker

## Alternatives considered

1. **Retry inline kèm backoff** — đơn giản nhất, nhưng chết máy là vẫn mất webhook.
2. **Message broker (Redis streams)** — thêm hạ tầng phải vận hành cho đúng một ca dùng.
3. **Outbox + worker (chọn)** — đạt at-least-once mà chỉ cần postgres + một consumer.
"""

FILES["21_proposals/PROPOSAL-002-psp-adapter.md"] = """---
id: PROPOSAL-002
issue_ref: ISSUE-003
problem: "Hai service gọi thẳng SDK của PSP, lặp lại logic retry và xử lý lỗi"
proposed: "Dồn toàn bộ lưu lượng PSP qua payment-adapter; cấm gọi thẳng"
impact: "Đổi Architecture: payment-adapter thành lối ra PSP duy nhất"
---

# PROPOSAL-002 — Single PSP egress

## Alternatives considered

1. **Thư viện wrapper SDK dùng chung** — vẫn N nơi gọi, N config phải xoay khoá.
2. **Allowlist theo từng service** — có chính sách mà không có chỗ cưỡng chế.
3. **Adapter làm lối ra duy nhất (chọn)** — một chỗ lo retry, khoá, và audit.
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

FILES["22_decisions/DECISION-001-outbox.md"] = decision(1, 1, "approved", "Đạt at-least-once mà thêm rất ít hạ tầng mới", "Thêm bảng outbox + worker gửi webhook")
FILES["22_decisions/DECISION-002-psp-adapter.md"] = decision(2, 2, "approved", "Một lối ra duy nhất để quản khoá, retry và audit", "Gọi PSP ngoài chỉ qua payment-adapter")

def backlog(n, desc, src, status):
    return """---
id: BACKLOG-%03d
description: "%s"
source_ref: %s
status: %s
---

# BACKLOG-%03d — %s
""" % (n, desc, src, status, n, desc)

FILES["23_backlog/BACKLOG-001-outbox-migration.md"] = backlog(1, "Migration bảng outbox", "DECISION-001", "done")
FILES["23_backlog/BACKLOG-002-delivery-worker.md"] = backlog(2, "Worker gửi webhook + dead-letter", "DECISION-001", "done")
FILES["23_backlog/BACKLOG-003-psp-cutover.md"] = backlog(3, "Chuyển đổi sang PSP adapter", "DECISION-002", "done")
FILES["23_backlog/BACKLOG-004-retry-backoff.md"] = backlog(4, "Retry webhook với backoff luỹ thừa", "ISSUE-004", "in-progress")
FILES["23_backlog/BACKLOG-005-idempotent-intake.md"] = backlog(5, "Khoá idempotent cho luồng nhận đơn", "DECISION-001", "open")

FILES["92_audit/LOG.md"] = """# Audit log

> Chỉ ghi thêm. Định dạng: `YYYY-MM-DD | chuyện gì đã xảy ra | ref | lệch ("-" nếu không) | vì sao`

2026-05-02 | khởi tạo bộ khung docs | - | - | -
2026-05-10 | ISSUE-001 chuyển về runbook, đóng lại | ISSUE-001 | - | nhiễu vận hành, không phải thay đổi
2026-05-28 | mở ISSUE-002 | ISSUE-002 | - | -
2026-06-05 | soạn PROPOSAL-001 | PROPOSAL-001 | - | -
2026-06-14 | duyệt DECISION-001, architecture lên REV A | DECISION-001 | - | -
2026-06-16 | BACKLOG-001 xong — migration outbox | BACKLOG-001 | - | -
2026-06-20 | BACKLOG-002 xong — worker gửi webhook đã chạy | BACKLOG-002 | - | -
2026-06-24 | mở ISSUE-003 | ISSUE-003 | - | -
2026-06-30 | soạn PROPOSAL-002 | PROPOSAL-002 | - | -
2026-07-02 | duyệt DECISION-002, architecture lên REV B | DECISION-002 | - | -
2026-07-15 | đẩy hotfix trước khi có Issue | ISSUE-004 | Issue lập bù về sau | bão webhook trên prod
2026-07-28 | BACKLOG-003 xong — chuyển đổi sang PSP adapter | BACKLOG-003 | - | -
"""

FILES["03_business-logic/refund-approval.md"] = """---
domain: "Duyệt hoàn tiền — điều kiện nào được hoàn, khi nào phải từ chối"
amended_by: []
---

# Refund approval

> Layer 1 — Foundation. Chỉ Decision workflow mới sửa được.

```flowchart
title: Duyệt hoàn tiền
trigger: merchant gọi POST /refunds
code: internal/order/refund.go
decide: within_window — trong 30 ngày kể từ capture?
decide: amount_ok — số tiền ≤ phần đã capture?
decide: psp_ok — PSP trả về thành công?
start -> within_window
within_window -> reject : quá hạn
within_window -> amount_ok : còn hạn
amount_ok -> reject : vượt quá
amount_ok -> call_psp : hợp lệ
call_psp -> psp_ok
psp_ok -> call_psp : lỗi tạm, backoff
psp_ok -> mark_refunded : thành công
mark_refunded ~> outbox : refund.completed
mark_refunded -> end
reject -> end
outcome: đơn ở trạng thái refunded, hoặc bị từ chối kèm lý do
```

## Rules

| Trong 30 ngày | Số tiền | Kết quả |
|---|---|---|
| không | — | `reject` — quá hạn |
| có | > phần đã capture | `reject` — vượt quá |
| có | ≤ phần đã capture | gọi PSP, retry có backoff |

## Invariants

- Tổng đã hoàn không bao giờ vượt tổng đã capture của đơn đó.
- `orders.status` chỉ đổi sang `refunded` sau khi PSP xác nhận — không đoán trước.
"""

FILES["03_business-logic/order-lifecycle.md"] = """---
domain: "Vòng đời đơn hàng — orders.status đi qua những trạng thái nào"
amended_by: []
---

# Order lifecycle

> Layer 1 — Foundation. Chỉ Decision workflow mới sửa được.

```state
title: Vòng đời đơn hàng
entity: orders.status
code: internal/order/state.go
initial: pending
final: delivered, refunded, cancelled
state: pending — đơn đã tạo, chưa capture được tiền
state: paid — đã capture, chờ kho đóng gói
state: shipped — đã bàn giao cho đơn vị vận chuyển
state: delivered — khách đã nhận hàng
state: refunded — đã hoàn tiền, PSP xác nhận
state: cancelled — huỷ khi chưa thu được tiền
pending -> paid : payment.succeeded
pending -> pending : retry capture, backoff luỹ thừa
pending -> cancelled : khách huỷ hoặc quá hạn giữ chỗ
paid ~> shipped : job đóng gói chạy nền
shipped -> delivered : carrier webhook giao thành công
shipped -> paid : vận chuyển trả hàng về kho
paid -> refunded : hoàn tiền được duyệt
delivered -> refunded : hoàn sau khi giao
```

## Invariants

- Ra khỏi `pending` là một chiều: đã capture thì không quay lại chưa capture.
- `cancelled` chỉ đến từ `pending` — sau khi thu tiền thì đường ra là `refunded`.
- Mỗi lần đổi trạng thái ghi một dòng vào bảng `order_events`, kể cả retry.
"""

FILES["30_conventions/coding-style.md"] = "# Coding style\n\nGo fmt, test dạng bảng.\n"
FILES["30_conventions/review-rules.md"] = "# Review rules\n\nĐổi schema cần hai lượt duyệt.\n"
FILES["40_services/order-service.md"] = "# order-service\n\nSở hữu trạng thái đơn.\n"
FILES["50_runbooks/gateway-502.md"] = "# Gateway 502\n\nKiểm tra sức khoẻ upstream.\n"
FILES["50_runbooks/psp-outage.md"] = "# PSP outage\n\nXếp hàng capture, báo cho merchant.\n"
FILES["50_runbooks/webhook-storm.md"] = "# Webhook storm\n\nTạm dừng worker, xả dead-letter.\n"
FILES["70_deploy/environments.md"] = "# Environments\n\nstaging, prod (một region).\n"
FILES["93_qa/test-matrix.md"] = "# Test matrix\n\nNhận đơn, capture, hoàn tiền, webhook.\n"
FILES["README.md"] = "# docs\n\nTài liệu ba lớp. Bản hướng dẫn 30 giây nằm ở đây trong scaffold thật.\n"

for folder in ["60_fe-integration"]:
    (docs / folder).mkdir(parents=True, exist_ok=True)

for rel, content in FILES.items():
    p = docs / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

print("fixture ready at", root)
