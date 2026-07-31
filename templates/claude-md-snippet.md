<!-- docs-kit:start (managed by /docs-kit:docs-init — edit between markers only via docs-kit) -->
## Documentation rules (docs-kit)

Repo này dùng mô hình docs ba lớp trong `docs/` — đọc `docs/README.md` trước (30 giây).

**Luật cứng:** chỉ Decision workflow mới được đổi `docs/02_architecture/` — mỗi lần
sửa phải nối một dòng `amended_by` dẫn Decision đã duyệt, ngay trong phiên nó được duyệt.

**Ngôn ngữ:** khung tiếng Anh, giải thích tiếng Việt. Tên trường frontmatter, giá trị
enum, tiền tố id, tiêu đề mục và các thuật ngữ (Issue, Proposal, Decision, Backlog,
Architecture, fast lane, full lane) giữ nguyên tiếng Anh. Phần diễn giải — description,
why, reason, dòng audit — viết tiếng Việt, để thuật ngữ Anh nằm trần trong câu.

**Lane test** — hai câu hỏi, "có" một câu → full lane (Issue → Proposal → Decision →
Backlog); "không" cả hai → fast lane (Issue → Backlog):
1. Thay đổi này có sửa tài liệu Architecture không?
2. Nếu hoá ra sai, rollback có mất hơn 1 ngày không?

**Trigger bắt buộc:**

| Sự kiện trong phiên | Việc phải làm với docs |
|---|---|
| Code đụng tới schema, API contract, hoặc ranh giới component | Phải có sẵn một Decision. Chưa có: tạo Issue, dừng lại, hỏi người dùng. |
| Một Backlog item hoàn thành | Đặt `status: done` + nối một dòng vào `docs/92_audit/`. |
| Một Decision được duyệt | Sửa `docs/02_architecture/` NGAY trong phiên đó. |
| Bắt đầu việc không có trong Backlog | Tạo Issue trước khi viết code. |

Phiên nào có đổi code thì kết thúc bằng `/docs-kit:docs-sync`; kiểm tra cấu trúc bằng `/docs-kit:docs-check`.
<!-- docs-kit:end -->
