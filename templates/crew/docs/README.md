# crew — bản đồ 30 giây

Tầng thi hành của docs-kit trong repo này. Backlog item là đơn vị công việc,
`scripts/crew` là công cụ, và bảy tệp trong thư mục này là luật vận hành.
Nguồn chân lý đầy đủ là `EXECUTION.md` trong plugin docs-kit; khi hai bên lệch
nhau thì EXECUTION.md thắng.

## Vòng đời một việc

```
Issue → (lane test, 3 câu — gates.md) → Backlog item
      → scripts/crew new <nnn>     # một executor rảnh mở nhánh work/b<nnn>
      → làm trọn trong executor đó, commit cuối mang "Closes: BACKLOG-<nnn>"
      → scripts/crew done <nnn>    # merge + 2 phép kiểm + đóng phiếu + thả executor
```

Và một vòng ngoài, nhịp tuần:

```
scripts/crew report --write    # đo git + docs/, viết docs/92_audit/reports/<tuần>.md
      → điền phần phán đoán, đồng bộ cột ## Now cho bằng phiếu open/in-progress
      → một dòng LOG.md, cột ref dẫn ĐƯỜNG DẪN tệp báo cáo chứ không dẫn id phiếu mở
```

Không có phiếu thì không có nhánh: `crew new` từ chối id chưa tồn tại trong
`docs/23_backlog/`, vì id cấp trong worktree sẽ trùng nhau một cách tất định.

## Bảy tệp

| Tệp | Trả lời câu |
|---|---|
| `roles.md` | ai làm gì, ai cố ý không làm gì; ai cầm bút trên tệp nào |
| `tickets.md` | phiếu to bao nhiêu thì chẻ, ba mức thi hành |
| `worktrees.md` | pool executor, nhánh, và vì sao gộp là một lệnh |
| `resources.md` | tài nguyên dùng chung, khoá, nhịp nhận phiếu |
| `gates.md` | bốn cổng trước khi hỏi người dùng quyết |
| `setup.md` | dựng lại hệ từ số 0, chỉnh ngưỡng |
| `README.md` | tệp này |

## Khi crew làm sai

Không ghi vào bảy tệp này, mà tạo một file trong `docs/99_feedback/` với
`about: crew`:

```bash
bash "$PLUGIN_ROOT/scripts/docs_feedback.sh" new <slug>
```

File đó copy nguyên văn là gửi được cho docs-kit. Luật đầy đủ ở EXECUTION §12;
điều đáng nhớ nhất là **một cách lách đã dùng có giá trị hơn một ý kiến**, vì
ngưỡng trong `resources.md` và `tickets.md` mới chỉ đo trên vài phiếu.

## Trạng thái nằm ở đâu

`../<repo>-crew/` — ngoài mọi bản checkout, nên mọi phiên nhìn chung một bảng
khoá. `scripts/crew status` đọc nó và trả lời năm câu: cây chính đang đứng ở
nhánh nào, cây nào đang mở, khoá nào đang giữ, lộ trình còn khớp thực tế không,
và có nên nhận thêm phiếu không.
