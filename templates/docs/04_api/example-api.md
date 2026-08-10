---
service: ""         # tên component phát ra contract này — phải trùng một tên trong 02_architecture
protocol: http      # http | grpc | graphql | event
base: ""            # tuỳ chọn. Base path, package proto, hoặc tiền tố topic
generated_from: ""  # tuỳ chọn. Đường dẫn tới artifact sinh tự động: openapi.json hoặc *.proto
amended_by: []      # chỉ Decision workflow được ghi. "- YYYY-MM-DD DECISION-NNN <tóm tắt>"
rejected: []        # tuỳ chọn. "- DECISION-NNN <đã loại cái gì>"
verified_at: ""     # tuỳ chọn. git rev lúc đọc code lần cuối
---

# API contract

> Layer 1 — Foundation. **Không sửa tài liệu này ngoài Decision workflow.**
> [STANDARD §6](../README.md) vốn đã bắt "code đụng API contract thì phải có Decision
> trước" — trước đây contract không có chỗ nào để nằm ngoài layer 3, nơi luật lại nói
> không cần Decision. Thư mục này đóng đúng mâu thuẫn đó.

`service:` phải trùng một tên trong `components` của `02_architecture/`. Đó là khớp nối
duy nhất giữa hai tài liệu, và validator kiểm nó — sai tên thì contract này treo lơ lửng,
không gắn vào service nào.

## Operations

Khối ```` ```api ```` dưới đây là **ví dụ chạy được** — nó biến thành bảng trên
`current.html`. Xoá đi khi viết contract thật, hoặc sửa đè lên.

```api
title: Orders public API
base: /v1
code: <thư mục chứa router/handler>
GET /orders/{id} -> Order — đọc một đơn, 404 nếu không thuộc merchant đang gọi
POST /orders <- CreateOrder -> Order — tạo đơn, idempotent theo header Idempotency-Key
DELETE /orders/{id} — huỷ đơn khi chưa capture
event order.paid -> OrderPaid — phát sau khi capture thành công
```

| Dòng | Nghĩa |
|---|---|
| `title:` `base:` `code:` | Header, đều không bắt buộc |
| `<VERB> <path>` | Một operation. `VERB` viết hoa: `GET`, `POST`, `RPC`, `QUERY`… |
| `event <tên>` | Một sự kiện service này phát ra |
| `<- <Type>` | Kiểu dữ liệu nhận vào |
| `-> <Type>` | Kiểu dữ liệu trả về |
| ` — <chú thích>` | Giải thích, dùng chung dấu phân cách với `decide:`, `state:` |

**Cố ý tối giản.** Status code, kiểu từng field, schema payload **không** viết ở đây —
chúng thuộc về artifact sinh tự động (OpenAPI, proto, route table). Đó là nửa hay đổi:
chép tay vào đây thì sang sprint sau là lệch, và đặt nửa hay đổi ấy sau cổng Decision chỉ
khiến người ta tìm cách lách cổng.

Thứ không generator nào nói được, nên nằm ở đây: **ranh giới có những operation nào, mỗi
cái nghĩa là gì, và service này cố ý KHÔNG expose cái gì.** Nửa đó gần như không đổi —
đúng thứ xứng đáng đi qua Decision.

## Generated half

`generated_from:` trỏ tới artifact mà repo **đã tự sinh** — `openapi.json`, `*.proto`.
Renderer đọc nó lúc render và in danh sách operation thật bên cạnh phần intent ở trên,
đánh dấu ba trạng thái:

| Trạng thái | Nghĩa |
|---|---|
| khớp | Có ở cả hai — không phải làm gì |
| `artifact only` | **Endpoint đang chạy mà không ai mô tả.** Theo STANDARD §6, thêm nó lẽ ra phải đi qua một Decision |
| `documented only` | Contract mô tả nhưng artifact không có — tài liệu đang nói sai |

Chi phí đồng bộ của nửa này bằng **0**: không ai bảo trì nó, nó được đọc lại mỗi lần
render. Đó chính là điều khiến phần intent ở trên đáng đi qua cổng Decision — phần hay
đổi đã không còn là tài liệu nữa.

Chốt bằng CI:

```bash
docs_render.sh --check-api .
```

`0` = khớp · `1` = có operation lệch, hoặc không đọc được artifact. **Đọc không được
cũng là lỗi** — một cổng âm thầm không chạy đúng là kiểu hỏng mà cổng này sinh ra để chặn.

docs-kit **không sinh** artifact và sẽ không bao giờ sinh: làm việc đó nghĩa là phải biết
framework (Gin khác Express khác FastAPI), trong khi kỷ luật của bộ detector là chỉ đọc
sự thật đã được khai báo. Nó chỉ tiêu thụ một định dạng chuẩn.

OpenAPI phải là **JSON**. Sàn portability là python 3.9 *stdlib* — có parser JSON, không
có parser YAML, và một parser YAML tự viết đọc sai contract còn tệ hơn là từ chối đọc.
Trỏ `generated_from` vào `openapi.json`; `.yaml` sẽ báo lỗi rõ ràng chứ không đoán bừa.

Sự kiện (`event ...`) không nằm trong so sánh: OpenAPI không mô tả event, nên đếm nó là
"thiếu" sẽ khiến check kêu oan ở mọi contract đúng.

## Không expose

_Cái gì cố tình để bên trong, và vì sao. Đây là phần Decision thật sự bảo vệ —
một endpoint bị thêm vào lặng lẽ là cách một ranh giới rò rỉ._

## Compatibility

_Phá vỡ contract thì báo ở đâu, giữ bản cũ bao lâu, deprecate thế nào. Dẫn Decision
đã duyệt việc đó._
