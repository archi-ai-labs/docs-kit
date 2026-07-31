---
id: ISSUE-000
description: "EXAMPLE — thống nhất một định dạng log có cấu trúc cho toàn bộ service"
why: "Debug xuyên service bằng grep trên log thuần text vừa chậm vừa dễ sót; log có trường rõ ràng thì truy được vết sự cố"
lane: full
status: promoted
---

# ISSUE-000 — Example: adopt a structured logging format

> **Ví dụ chạy được** do docs-init tạo sẵn. Nó minh hoạ trọn chuỗi full lane:
> ISSUE-000 → PROPOSAL-000 → DECISION-000 → BACKLOG-000 (+ một dòng trong `92_audit/`).
> Xoá cả bốn file `-000` cùng lúc (chúng dẫn chiếu lẫn nhau), hoặc giữ lại làm mẫu
> định dạng. Issue thật bắt đầu từ `ISSUE-001`.

## Notes

Lane test: nó **không** sửa tài liệu Architecture (câu 1 = không), nhưng rollback
định dạng này trên toàn bộ service thì mất hơn một ngày (câu 2 = có) → **full lane**.

Một Issue khởi đầu ở `status: exploring` khi còn là nghiên cứu thô, chuyển sang
`open` khi đã là ứng viên thật, `promoted` khi đã có Proposal (full lane) hoặc đã
có Backlog item (fast lane), và `archived` khi bị bỏ hoặc bị thay thế.
