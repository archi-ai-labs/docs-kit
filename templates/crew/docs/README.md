# crew — bản đồ 30 giây

Tầng thi hành của docs-kit trong repo này. Backlog item là đơn vị công việc,
`scripts/crew` là công cụ, và bảy tệp trong thư mục này là luật vận hành.
Nguồn chân lý đầy đủ là `EXECUTION.md` trong plugin docs-kit; khi hai bên lệch
nhau thì EXECUTION.md thắng.

## Vòng đời một việc

```
Issue → (lane test, 3 câu — gates.md) → Backlog item
      → scripts/crew new <nnn>     # cây ../<repo>-b<nnn>, nhánh work/b<nnn>
      → làm trọn trong cây đó, commit cuối mang "Closes: BACKLOG-<nnn>"
      → scripts/crew done <nnn>    # merge + 2 phép kiểm + đóng phiếu + dọn cây
```

Không có phiếu thì không có cây: `crew new` từ chối id chưa tồn tại trong
`docs/23_backlog/`, vì id cấp trong worktree sẽ trùng nhau một cách tất định.

## Bảy tệp

| Tệp | Trả lời câu |
|---|---|
| `roles.md` | ai làm gì, ai cố ý không làm gì |
| `tickets.md` | phiếu to bao nhiêu thì chẻ, ba mức thi hành |
| `worktrees.md` | cây, nhánh, và vì sao gộp là một lệnh |
| `resources.md` | tài nguyên dùng chung, khoá, nhịp nhận phiếu |
| `gates.md` | bốn cổng trước khi hỏi người dùng quyết |
| `setup.md` | dựng lại hệ từ số 0, chỉnh ngưỡng |
| `README.md` | tệp này |

## Trạng thái nằm ở đâu

`../<repo>-crew/` — ngoài mọi bản checkout, nên mọi phiên nhìn chung một bảng
khoá. `scripts/crew status` đọc nó và trả lời ba câu: cây nào đang mở, khoá nào
đang giữ, có nên nhận thêm phiếu không.
