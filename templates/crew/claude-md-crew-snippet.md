<!-- docs-kit:crew:start (managed by /docs-kit:crew-init — edit between markers only via docs-kit) -->
## Execution rules (docs-kit crew)

Repo này chạy tầng thi hành crew — luật đầy đủ trong `.claude/crew/`, đọc
`README.md` trước.

**Phiếu:** Backlog item là đơn vị công việc. Một phiếu – một nhánh – một phiên,
làm trọn tới `done`. Không có phiếu trong `docs/23_backlog/` thì không có nhánh.

**Executor là cây thường trực** `../<repo>-e<k>`, dựng một lần rồi dùng lại qua
nhiều phiếu. Nhánh nó đang mở là phiếu nó giữ, HEAD tách rời là nó rảnh.

**Title phiên** `<repo> · <chỗ> · b<nnn> · <trạng thái> · crew/executor`, do
`crew name executor` tự đọc: chỗ là `e<k>`, hoặc `main` với fast-pair. Trạng
thái đi `processing` → `finishing` (commit mang trailer **và** cây sạch) →
`finished` (phiếu đã đóng sổ); chạy lại lệnh sau mỗi lần đổi.

**Lệnh:** `scripts/crew new <nnn>` giao phiếu cho một executor rảnh (nhánh
`work/b<nnn>`), hết cây rảnh thì tự dựng thêm; `scripts/crew done <nnn>` gộp, và
**không gõ tay sáu lệnh trong ruột nó**; `scripts/crew lock` trước phần chạm
máy thật; `scripts/crew status` trước khi nhận thêm phiếu.

**Ba mức thi hành** (`execution:` trong phiếu): `fast-pair` = sửa thẳng nhánh dev
ở cây chính, ≤ 1 tệp, commit ngay trong lượt; `fast` và `full` = một executor,
khác nhau ở chỗ `full` đã có Decision. Chi tiết: `.claude/crew/tickets.md`.

**Lane test có BA câu** (câu 3: có thao tác không lùi được không — nó thắng
hai câu kia). "Không" cả ba → khai `LANE: fast — <lý do>` ngay trong trả lời.
Trước khi hỏi người dùng quyết việc full lane: giải thích đạt cổng 1 rồi một
câu kiểm mức 2 — luật trong `.claude/crew/gates.md`; user cần bản giải thích
chuẩn cho bất kỳ vấn đề nào thì gõ `/docs-kit:explain <vấn đề>`.

**Commit đóng phiếu mang trailer** `Closes: BACKLOG-<nnn>` để audit dẫn sha.

**Crew làm sai thì ghi lại, đừng chỉ nói.** `docs_feedback.sh new <slug>` với
`about: crew` — file đó copy nguyên văn là gửi đi được, còn phiên chat thì hết
phiên là mất.
<!-- docs-kit:crew:end -->
