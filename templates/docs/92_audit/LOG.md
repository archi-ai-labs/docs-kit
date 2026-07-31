# Audit log — append-only

Review là READ-ONLY trên layer 1–2: mọi phát hiện đổ về đây và chỉ ở đây.
Mỗi sự kiện một dòng, **nối vào cuối file**. Không bao giờ chèn giữa, sửa, hay xoá
dòng cũ — `docs-check` đối chiếu file này với git HEAD.

Định dạng: `YYYY-MM-DD | chuyện gì đã xảy ra | ref | lệch so với Decision/Backlog ("-" nếu không) | vì sao`

---

{{DOCS_KIT_DATE}} | khởi tạo bộ khung docs bằng docs-kit | - | - | dòng mốc ban đầu
{{DOCS_KIT_DATE}} | BACKLOG-000 hoàn thành (ví dụ mẫu) | BACKLOG-000 (DECISION-000) | - | minh hoạ trigger hoàn thành
