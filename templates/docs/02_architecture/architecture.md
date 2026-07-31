---
components: []      # "name [kind] `path/in/repo` — nó LÀ GÌ, một câu"
data_flow: []       # "a -> b : nhãn" mỗi dòng một cạnh; "~>" cho async
tech_stack: []
constraints: []
amended_by: []
---

# Architecture

> Layer 1 — Foundation. **Không sửa tài liệu này ngoài Decision workflow.**
> Mỗi lần sửa phải nối thêm một dòng vào `amended_by` trong frontmatter:
> `- YYYY-MM-DD DECISION-NNN <tóm tắt một dòng>` — viết ngay trong phiên mà
> Decision được duyệt. Hook PostToolUse của docs-kit sẽ cảnh báo mọi lần sửa ở đây.

## Components

Danh sách có thẩm quyền là `components` trong frontmatter. Mỗi dòng một
component, cú pháp phẳng — **không lồng nhau**:

```yaml
components:
  - engine `src/engine/match.go` — khớp lệnh limit/market, order book giữ trong RAM
  - store [db] `deploy/pg/` — postgres, nguồn sự thật sau khi commit
  - jobs [queue] `src/worker/` — worker nền, retry có backoff
```

`[kind]` là một trong `db` · `queue` · `ui` · `svc` (mặc định). Đường dẫn trong
backtick là **chỗ đọc code**. Phần mô tả phải trả lời "nó là gì" — viết sau khi
đã đọc source, không suy từ cái tên.

Muốn giải thích dài hơn thì mở một mục `### <tên component>` bên dưới; card
tương ứng trên `current.html` sẽ tự gắn phần đó vào.

## Data flow

Danh sách có thẩm quyền là `data_flow` trong frontmatter. Mỗi dòng một cạnh:

```yaml
data_flow:
  - api -> engine : validate + idempotency key
  - engine -> ledger : ghi bút toán kép
  - engine ~> audit : append trade event
```

Renderer luôn vẽ **graph** (STANDARD §10). Chu trình không phải lỗi — `a -> b`
kèm `b -> a` là callback, là đọc cache ngược, là retry — nên cạnh quay ngược
được vẽ thành **back-edge chạy dưới các hàng**. Quá dày thì hình vẫn vẽ đủ, chỉ
cuộn ngang, kèm gợi ý tách bớt sang doc khác. Không bao giờ thu nhỏ hình cho
vừa cột.

## Data model

Components ở trên trả lời "có những gì" cho service. Khối ```` ```erd ```` dưới đây
trả lời đúng câu đó cho dữ liệu. Đây là **ví dụ chạy được** — nó biến thành hình
trên `current.html`. Xoá đi khi viết lược đồ thật, hoặc sửa đè lên.

```erd
title: Lược đồ <hệ thống>
code: <file schema/migration để đọc>

table: accounts
id           uuid   pk
email        text   unique
created_at   timestamptz

table: orders
id           uuid    pk
account_id   uuid    fk -> accounts.id — ai đặt đơn này
status       text
total_cents  bigint

table: order_items
id         uuid   pk
order_id   uuid   fk -> orders.id
sku        text
qty        int
```

| Dòng | Nghĩa |
|---|---|
| `title:` `code:` | Header, đều không bắt buộc |
| `table: <tên>` | Mở một bảng. Mọi dòng sau nó là cột, cho tới `table:` tiếp theo |
| `<tên> <kiểu> <cờ…>` | Một cột. Các cờ viết thứ tự nào cũng được |
| `pk` | Khoá chính |
| `fk -> <bảng>.<cột>` | Khoá ngoại — **đây chính là thứ vẽ ra quan hệ** |
| `unique` | Trên cột fk thì quan hệ thành 1:1 |
| `null` | Cột cho phép rỗng — quan hệ không bắt buộc |

**Không có cú ph��p quan hệ, và không ai gõ cardinality bằng tay.** Khoá ngoại
*chính là* quan hệ, và ý nghĩa của nó không phải chuyện quan điểm: nhiều dòng con
trỏ về một dòng cha. Nên đầu con vẽ chân quạ, đầu cha vẽ gạch đơn, `unique` biến
đầu con thành gạch đơn, `null` thêm vòng tròn rỗng. N:M là bảng trung gian hai fk
— đúng như schema thật vẫn có.

Quan hệ tự trỏ (`parent_id fk -> orders.id`) viết như mọi cột khác; renderer nhận
ra nó quay ngược và vẽ xuống làn dưới các hàng.

## Types & contracts

Data model ở trên là dữ liệu đã lưu. Khối ```` ```class ```` dưới đây là code —
cái nào implement interface nào, cái nào giữ tham chiếu tới cái nào. Cũng là
**ví dụ chạy được**, xoá hoặc sửa đè khi viết thật.

```class
title: <ranh giới quan trọng nhất của hệ thống>
code: <package đọc để hiểu>

interface: Store
+ Get(id string) (Record, error)
+ Put(r Record) error

class: PostgresStore
implements Store
- pool    *pgxpool.Pool
- last    Record — bản ghi ghi gần nhất, dùng cho metric
+ Get(id string) (Record, error)
+ Put(r Record) error

class: MemoryStore
implements Store
- items map[string]Record
+ Get(id string) (Record, error)
+ Put(r Record) error

class: Record
+ ID      string
+ Payload []byte
```

| Dòng | Nghĩa |
|---|---|
| `class: <tên>` · `interface: <tên>` | Mở một type. Interface được vẽ kèm nhãn `«interface»` |
| `implements <tên>` | Cạnh nét đứt, tam giác rỗng ở đầu interface |
| `extends <tên>` | Cạnh nét liền, tam giác rỗng ở đầu type cha |
| `+ <tên> <kiểu>` · `- <tên> <kiểu>` | Thành viên public · private |
| Thành viên có `(` | Là method — nằm ở ngăn dưới |

**Association không viết tay.** Một field có kiểu trùng tên một type đã khai báo
trong khối này thì tự sinh ra cạnh, y như `fk` sinh ra quan hệ ở ERD. Chữ ký
method **không** quét — một signature nhắc đủ mọi type trong package sẽ vẽ ra đồ
thị không ai đọc được.

Không có composition/aggregation: ranh giới giữa hai cái đó gây tranh cãi nhiều
hơn là làm sáng ra, và viết tay thì sớm muộn cũng lệch với code.

## Business flows

Mỗi kịch bản nghiệp vụ một khối ```` ```flow ````. Đây là chỗ trả lời "làm việc X
thì chuyện gì xảy ra, theo thứ tự nào" — thứ mà sơ đồ component tĩnh không nói được.

````markdown
```flow
title: <tên kịch bản>
trigger: <cái gì khởi động nó>
code: <file/thư mục đọc để hiểu bước này>
a -> b : bước này làm gì
b -> b : tự xử lý bên trong chính nó
b ~> c : bước async
outcome: <kết thúc thì hệ thống ở trạng thái nào>
```
````

## Tech stack

_Ngôn ngữ, framework, datastore, hạ tầng. Khớp với `tech_stack` phía trên._

## Constraints

_Ràng buộc cứng mà thiết kế phải tôn trọng: độ trễ, chi phí, tuân thủ, quy mô team…_

## Amendment history

Danh sách có thẩm quyền là `amended_by` trong frontmatter. Mục này chỉ để ghi thêm
bối cảnh cho những lần sửa đáng kể, khi một dòng tóm tắt là không đủ.
