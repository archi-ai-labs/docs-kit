<!-- docs-kit:start (managed by /docs-kit:docs-init — edit between markers only via docs-kit) -->
## Documentation rules (docs-kit)

Code là sản phẩm, `docs/` là thứ hỗ trợ code. Khối này chỉ giữ những việc bắt buộc
trong phiên; phần còn lại nằm ở `docs/README.md` và chỉ đọc khi cần.

**Chỉ Decision workflow mới được sửa** `docs/02_architecture/`,
`docs/03_business-logic/` và `docs/04_api/`. Mỗi lần sửa phải nối một dòng
`amended_by` dẫn Decision đã duyệt, ngay trong phiên Decision đó được duyệt.

| Sự kiện | Việc phải làm |
|---|---|
| Code đụng schema, API contract hoặc ranh giới component | Phải có Decision sẵn. Chưa có thì tạo Issue rồi dừng lại hỏi người dùng. |
| Bắt đầu việc không có trong Backlog | Tạo Issue trước khi viết code. |
| Một Decision vừa được duyệt | Sửa layer 1 ngay trong phiên đó. |

**Xong một Backlog item thì viết `Closes: BACKLOG-NNN` vào commit message**, đừng sửa
tay. `docs_close.sh --apply .` đặt `status: done` và ghi dòng audit trích đúng sha.

**Chỉ chạy `/docs-kit:docs-sync` khi** hook cuối phiên gọi tên một tài liệu cụ thể,
hoặc ngay sau khi một Decision được duyệt. Phiên sửa code mà hook im lặng thì không
cần chạy, vì im lặng nghĩa là không tài liệu nào nhận những file vừa đổi.

Đọc `docs/INDEX.md` trước rồi mở đúng id cần, đừng glob cả thư mục. docs-kit làm sai
hoặc phải lách mới xong việc thường thì ghi `docs_feedback.sh new <slug>`.
<!-- docs-kit:end -->
