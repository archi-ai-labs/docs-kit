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

Renderer tự chọn kiểu vẽ theo độ dày (STANDARD §10): trong ngân sách thì vẽ
**graph**, quá dày hoặc có chu trình thì chuyển sang **matrix** kèm bảng cạnh
đầy đủ. Không bao giờ thu nhỏ hình cho vừa cột.

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
