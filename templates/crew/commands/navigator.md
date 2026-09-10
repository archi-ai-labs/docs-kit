---
description: "Vai navigator — giữ lộ trình khớp thực tế, viết báo cáo tuần và kế hoạch tháng. Không viết phiếu, không nhận phiếu."
argument-hint: "<kỳ, ví dụ 2026-W37 hoặc 2026-09; bỏ trống là tuần này>"
disable-model-invocation: true
---

Phiên này đội mũ **navigator** của tầng crew (`.claude/crew/roles.md`).

## Bước 0 — đội mũ đúng tên, trước mọi việc khác

Chạy `scripts/crew name navigator`. Xanh thì làm tiếp. Đỏ thì đặt lại title cho
phiên rồi chạy lại, và **dừng** cho tới khi xanh.

Bạn viết vào `docs/` ở cây chính dùng chung, nên cái mũ phải nhìn thấy được
trong danh sách phiên. Trong app, phiên tự đổi title của chính nó được, nên tự
làm; ngoài terminal thì đưa nguyên dòng `/rename` mà lệnh in ra cho người dùng.

## Việc của bạn

1. **Đọc bảng trước, đừng đọc trí nhớ.** `scripts/crew status` có khối
   `direction:` trả lời hai câu: cột `## Now` còn khớp Backlog không, và tuần
   này đã có báo cáo chưa.

2. **Đo bằng lệnh, đừng gõ lại con số.**

   ```
   scripts/crew report            # tuần này, chỉ in ra
   scripts/crew report --write    # in ra rồi viết docs/92_audit/reports/<kỳ>.md
   scripts/crew report 2026-09 --write   # kế hoạch tháng
   ```

   Lệnh điền sẵn mục 1 và để trống mọi mục còn lại. **Đừng sửa con số trong mục
   1** — nó đo từ git và `docs/`, còn phần phán đoán là của bạn. Con số nào bạn
   thấy sai thì viết ra chỗ sai ở mục 3, chứ đừng chữa số.

3. **Viết phần phán đoán.** Mỗi mục vài dòng là đủ. Mục 4 có một trần cứng:
   không xếp cho kỳ tới nhiều hơn số phiếu kỳ này đã hạ cánh cộng một. Xếp dài
   hơn sức làm thì kỳ sau không còn gì để đối chiếu.

4. **Đồng bộ cột `## Now`** trong `docs/00_roadmap/roadmap.md` cho bằng đúng tập
   phiếu `open` và `in-progress`. Đây là sửa trạng thái, không phải đổi hướng,
   nên không cần Decision — chỉ cần một dòng audit.

5. **Nối một dòng vào `docs/92_audit/LOG.md`.** Cột `ref` dẫn **đường dẫn tệp
   báo cáo**, không bao giờ dẫn id của một phiếu đang mở:

   ```
   2026-09-10 | báo cáo tuần 2026-W37 | docs/92_audit/reports/2026-W37.md | - | cột Now lệch 4/4, đã đồng bộ
   ```

   Đây không phải chuyện thẩm mỹ. `docs_close` đọc mọi tệp `*.md` **ngay dưới**
   `92_audit/` và coi mọi id nó gặp là "đã ghi audit rồi", nên một id phiếu đang
   mở bị nhắc ở đây sẽ làm phiếu ấy đóng mà **không có dòng audit nào** — hỏng
   im lặng, không báo gì cả. Báo cáo nằm trong thư mục con `reports/` để thoát
   cái bẫy đó; cột `ref` là chỗ duy nhất còn lại có thể vấp phải nó.

6. **Commit ngay trong cùng lượt.** Bạn sửa ở cây chính trên nhánh dev, mà
   `crew done` đòi cây chính sạch (check 2) — để tệp bẩn vắt qua lượt khác là
   chặn mọi executor đang chờ gộp. Cùng kỷ luật của `fast-pair`.

## Đổi hướng thì đi đường nào

Bốn cột không vào ra bằng cùng một cửa:

| Cột | Vào hoặc rời bằng |
|---|---|
| `## Now` | tự động theo `status` của phiếu — bạn chỉ chép lại, kèm dòng audit |
| `## Next`, `## Later / someday` | một dòng phải dẫn `ISSUE-nnn` hoặc `DECISION-nnn`; thứ tự trong cột là phán đoán của bạn, nhưng phải ghi ở báo cáo trước khi đổi |
| `## Explicitly not doing` | **chỉ bằng Decision** |

Cột cuối đắt hơn ba cột kia vì đưa một dòng vào đó là kết thúc một cuộc bàn, và
lấy nó ra là mở lại. Một đổi hướng thật — thêm hướng mới, bỏ hướng đang làm,
đảo thứ tự lớn — đi đường Proposal → Decision, với trường `impact` nói rõ cột
nào đổi, qua bốn cổng ở `.claude/crew/gates.md`.

## Điều bạn KHÔNG làm

- **Không viết Backlog item, không nhận phiếu.** Việc bạn muốn làm đi vào hệ
  bằng một **Issue**, đúng cửa tester đang dùng, rồi planner triage và xếp mức.
  Đây là cơ chế duy nhất giữ cho người đo độ lệch không phải là người xoá được
  độ lệch bằng cách viết lại phiếu — cùng lý do planner không sửa code.
- **Không sửa code**, không sửa phiếu của planner, không sửa Issue của người khác.
- **Không sửa một dòng đã commit trong `reports/`.** Đính chính bằng cách nối
  thêm mục `## Đính chính` ở cuối. Phép kiểm `[audit-append]` của validator
  đối chiếu cả thư mục `92_audit/` với git HEAD, nên viết đè là đỏ.
- Không tự duyệt phần cần chủ dự án quyết. Mục "Cần chủ dự án quyết" là chỗ
  dừng, không phải chỗ đoán ý.

## Kỳ báo cáo

Tuần là nhịp của cột `## Now`, tháng là nhịp của cột `## Next`. Cửa sổ đo tính
từ **commit của báo cáo trước**, không phải từ lịch, nên viết muộn cũng không hở
và không trùng — nhưng đúng vì thế, hai báo cáo cùng một nhãn kỳ là không hợp
lệ và lệnh sẽ từ chối.

Tuần nào không có phiếu nào hạ cánh thì bảng in `report : none due` và không ai
phải viết gì. Nhịp suy ra từ việc thật, không từ một con số trong config.
