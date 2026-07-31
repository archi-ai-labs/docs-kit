# docs/ — tài liệu ba lớp

Bộ khung do docs-kit tạo. Chuẩn đầy đủ: `STANDARD.md` của docs-kit. Đọc file này
trước — mất 30 giây.

## 1 · Layers

| Layer | Thư mục | Bản chất | Luật sửa |
|---|---|---|---|
| 1 · Foundation | `00_roadmap` `01_products` `02_architecture` `03_business-logic` | Trạng thái | **Chỉ** đổi qua một Decision đã duyệt (`amended_by`) |
| 2 · Change | `20_issues` `21_proposals` `22_decisions` `23_backlog` | Tiến trình, truy nguyên được | Theo đúng luồng bên dưới |
| 3 · Reference | `30_conventions` `40_services` `50_runbooks` `60_fe-integration` `70_deploy` `93_qa` | Tài liệu vận hành | Sửa thẳng, không cần Decision |
| Oversight | `92_audit` | Nhật ký chỉ ghi thêm | Chỉ nối dòng, không bao giờ viết lại |

## 2 · Flow

```
Issue (exploring → open)
  ├─ FAST lane ──────────────────────────────► Backlog (source_ref = Issue)
  └─ FULL lane ──► Proposal ──► Decision ────► Backlog (source_ref = Decision)
Decision được duyệt ⇒ sửa 02_architecture / 03_business-logic NGAY trong phiên đó (+ amended_by)
Backlog item xong   ⇒ status: done + nối một dòng vào 92_audit/
Review (định kỳ)    ⇒ read-only trên layer 1–2; phát hiện nối vào 92_audit/
```

## 3 · Lane test — hai câu hỏi, "có" một câu ⇒ FULL lane

1. Thay đổi này có sửa Architecture hay Business logic không?
2. Nếu hoá ra sai, rollback có mất hơn 1 ngày không?

## 4 · Folders

| # | Thư mục | Để làm gì (một dòng) |
|---|---|---|
| 00 | `00_roadmap` | Sản phẩm đang đi về đâu: now / next / later |
| 01 | `01_products` | Mỗi sản phẩm là gì, cho ai, thế nào là thành công |
| 02 | `02_architecture` | Component, lược đồ dữ liệu (```erd```), type (```class```), luồng dữ liệu, stack, ràng buộc — chỉ sửa qua Decision |
| 03 | `03_business-logic` | Quy tắc rẽ nhánh (```flowchart```) + vòng đời entity (```state```) — chỉ sửa qua Decision |
| 20 | `20_issues` | Mọi thứ đáng làm đều vào đây trước (nghiên cứu thô bắt đầu ở `exploring`) |
| 21 | `21_proposals` | Phương án cho full lane, kèm lựa chọn thay thế + đánh đổi |
| 22 | `22_decisions` | Duyệt / loại, do ai, vì sao |
| 23 | `23_backlog` | Việc làm được ngay, truy nguyên qua `source_ref` |
| 30 | `30_conventions` | Quy ước code / đặt tên / quy trình |
| 40 | `40_services` | Tra cứu service: cái gì chạy ở đâu, ai quản |
| 50 | `50_runbooks` | Quy trình vận hành từng bước |
| 60 | `60_fe-integration` | Contract và ghi chú cho tích hợp frontend |
| 70 | `70_deploy` | Ship kiểu gì: môi trường, pipeline, rollback |
| 92 | `92_audit` | Nhật ký chỉ ghi thêm — nơi tra cứu truy nguyên |
| 93 | `93_qa` | Chiến lược test, checklist QA, chỗ còn hổng |

## 5 · Traceability

`92_audit/` là chỗ tra *chuyện gì đã xảy ra, dưới Decision/Backlog nào, và lệch ra
sao*. Chỉ ghi thêm — được đối chiếu với lịch sử git.

Id (`ISSUE-`, `PROPOSAL-`, `DECISION-`, `BACKLOG-` + số 3 chữ số) nằm ở `id:` trong
frontmatter; mọi `*_ref:` đều trỏ tới một id, **không bao giờ trỏ tới tên file**.
Bốn file `*-000` đi kèm là một chuỗi ví dụ chạy được — xoá cả bốn cùng lúc, hoặc
giữ lại làm mẫu định dạng. Id thật bắt đầu từ `001`.

## 6 · Ngôn ngữ

Khung tiếng Anh, giải thích tiếng Việt. Tên thư mục, tên trường frontmatter, giá
trị enum (`open`, `in-progress`, `done`, `approved`, `rejected`, `fast`, `full`),
tiền tố id, tiêu đề mục, và các thuật ngữ (Issue, Proposal, Decision, Backlog,
Architecture, fast lane, full lane) giữ nguyên tiếng Anh — đổi chúng là hỏng
validator. Phần diễn giải viết tiếng Việt, để thuật ngữ Anh nằm trần trong câu.

Kiểm tra cấu trúc bất cứ lúc nào: `/docs-kit:docs-check` · Đối chiếu sau một phiên
làm việc: `/docs-kit:docs-sync`
