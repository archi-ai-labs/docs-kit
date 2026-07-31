---
domain: ""          # nghiệp vụ này là gì, một dòng
amended_by: []
---

# Business logic

> Layer 1 — Foundation. **Không sửa tài liệu này ngoài Decision workflow.**
> Mỗi lần sửa phải nối thêm một dòng vào `amended_by` trong frontmatter:
> `- YYYY-MM-DD DECISION-NNN <tóm tắt một dòng>` — viết ngay trong phiên mà
> Decision được duyệt. Hook PostToolUse của docs-kit sẽ cảnh báo mọi lần sửa ở đây.

Ranh giới với `02_architecture/`, để không phải đoán mỗi lần viết:

| Câu hỏi tài liệu trả lời | Ở đâu |
|---|---|
| Hệ thống gồm những gì, cái nào gọi cái nào | `02_architecture/` |
| Làm việc X thì chuyện gì xảy ra, theo thứ tự nào | `02_architecture/` — khối ```` ```flow ```` |
| **Gặp điều kiện Y thì rẽ đường nào, theo quy tắc gì** | **ở đây** |

## Flows

Mỗi quy tắc nghiệp vụ có rẽ nhánh một khối ```` ```flowchart ````. Đây là chỗ
trả lời "điều gì xảy ra khi…" — thứ mà sequence không nói được, vì sequence
không có điều kiện.

Khối dưới đây là **ví dụ chạy được** — nó biến thành hình trên `current.html`.
Xoá nó đi khi viết quy tắc thật, hoặc sửa đè lên.

```flowchart
title: Duyệt yêu cầu hoàn tiền
trigger: user bấm "Yêu cầu hoàn tiền"
code: src/refund/approve.go
decide: check_amount — số tiền > 2.000.000đ?
decide: has_history — khách từng bị từ chối chưa?
start -> check_amount
check_amount -> manual_review : yes
check_amount -> has_history : no
has_history -> manual_review : có
has_history -> auto_approve : chưa
manual_review -> notify
auto_approve -> notify
notify ~> ledger : ghi bút toán
notify -> end
outcome: đơn ở trạng thái approved hoặc pending_review
```

Cú pháp — cùng một họ với `data_flow` và ```` ```flow ````, không có ngôn ngữ thứ ba:

| Dòng | Nghĩa |
|---|---|
| `title:` `trigger:` `outcome:` `code:` | Header, đều không bắt buộc |
| `decide: <node> — <câu hỏi>` | Khai báo `<node>` là điểm rẽ, vẽ thành hình thoi |
| `a -> b` · `a ~> b` | Bước tuần tự · bước async |
| `a -> b : nhãn` | Nhãn cạnh. Trên cạnh ra từ điểm rẽ, nhãn **chính là** tên nhánh |
| `start` · `end` | Tên dành riêng, vẽ thành node bo tròn hai đầu |

Vòng lặp viết thẳng như một cạnh thường — `validate -> input : sai định dạng`.
Renderer nhận ra nó quay ngược và vẽ xuống làn dưới các hàng, không cần cú pháp
riêng.

## Rules

Quy tắc dạng bảng thì viết thành bảng — **không cần cú pháp riêng**, renderer đã
render markdown table sẵn. Một decision table đọc nhanh hơn mọi hình:

| Số tiền | Đã từng bị từ chối | Kết quả |
|---|---|---|
| > 2.000.000đ | — | `manual_review` |
| ≤ 2.000.000đ | có | `manual_review` |
| ≤ 2.000.000đ | chưa | `auto_approve` |

## Lifecycle

Một entity đi qua nhiều trạng thái thì viết một khối ```` ```state ````. Flowchart
ở trên trả lời "gặp điều kiện này thì rẽ đường nào"; chỗ này trả lời "nó đang ở
đâu, và sự kiện nào đẩy nó đi tiếp".

Khối dưới đây cũng là **ví dụ chạy được** — xoá hoặc sửa đè khi viết máy trạng
thái thật.

```state
title: Vòng đời đơn hàng
entity: orders.status
code: src/order/state.go
initial: pending
final: delivered, refunded, cancelled
state: pending — đơn đã tạo, chưa thu được tiền
state: paid — đã capture, chờ đóng gói
state: shipped — đã bàn giao cho đơn vị vận chuyển
pending -> paid : payment.succeeded
pending -> cancelled : khách huỷ trước khi trả
paid ~> shipped : job đóng gói chạy nền
shipped -> delivered : carrier webhook
paid -> refunded : hoàn tiền được duyệt
delivered -> refunded : hoàn sau khi giao
paid -> paid : retry capture
```

| Dòng | Nghĩa |
|---|---|
| `title:` `entity:` `code:` | Header, đều không bắt buộc. `entity:` là thứ mang vòng đời này |
| `initial: <state>` | Trạng thái bắt đầu — **một** cái, vẽ viền xanh |
| `final: a, b, c` | Các trạng thái kết thúc, vẽ viền đôi |
| `state: <tên> — <nghĩa>` | Khai báo tuỳ chọn. Khai báo một cái là bật luôn cảnh báo cho những cái còn thiếu |
| `a -> b : sự kiện` · `a ~> b : sự kiện` | Transition · transition do job nền thực hiện |

`initial:` và `final:` đánh dấu **trạng thái thật**, không đẻ ra node `start`/`end`
giả — máy sáu trạng thái phải hiện đúng sáu ô. Không có cú pháp guard: điều kiện
đáng vẽ thì đáng có một ```` ```flowchart ```` riêng ở phần Flows bên trên.

Vòng lặp (`paid -> paid`, `delivered -> refunded`) viết như transition thường —
renderer nhận ra nó quay ngược và vẽ xuống làn dưới các hàng.

## Invariants

_Những điều luôn đúng bất kể đi nhánh nào. Đây là thứ đáng viết ra nhất, vì nó
là cái test phải bảo vệ._
