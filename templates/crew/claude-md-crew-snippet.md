<!-- docs-kit:crew:start (managed by /docs-kit:crew-init — edit between markers only via docs-kit) -->
## Execution rules (docs-kit crew)

Repo này chạy tầng thi hành crew — luật đầy đủ trong `.claude/crew/` (bảy tệp,
đọc `README.md` trước, 30 giây).

**Phiếu:** Backlog item là đơn vị công việc. Một phiếu – một cây – một phiên,
làm trọn tới `done`. Không có phiếu trong `docs/23_backlog/` thì không có cây.

**Lệnh:** `scripts/crew new <nnn>` nhận phiếu (cây `../<repo>-b<nnn>`, nhánh
`work/b<nnn>`); `scripts/crew done <nnn>` gộp — sáu bước và hai phép kiểm nằm
trong ruột lệnh, **không gõ tay sáu lệnh đó**; `scripts/crew lock` trước phần
chạm máy thật; `scripts/crew status` trước khi nhận thêm phiếu.

**Ba mức thi hành** (`execution:` trong frontmatter phiếu): `fast-pair` = sửa
thẳng nhánh dev trong cây chính, ≤ 1 tệp, commit ngay trong lượt; `fast` = cây
riêng, không cần Decision; `full` = cây riêng, đã có Decision. Chi tiết:
`.claude/crew/tickets.md`.

**Lane test có BA câu** (câu 3: có thao tác không lùi được không — nó thắng
hai câu kia). "Không" cả ba → khai `LANE: fast — <lý do>` ngay trong trả lời.
Trước khi hỏi người dùng quyết việc full lane: giải thích đạt cổng 1 rồi một
câu kiểm mức 2 — luật trong `.claude/crew/gates.md`; user cần bản giải thích
chuẩn cho bất kỳ vấn đề nào thì gõ `/docs-kit:explain <vấn đề>`.

**Commit đóng phiếu mang trailer** `Closes: BACKLOG-<nnn>` để audit dẫn sha.
<!-- docs-kit:crew:end -->
