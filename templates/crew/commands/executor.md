---
description: "Vai executor — một phiếu, một cây, làm trọn tới done rồi tự gộp."
argument-hint: "<số phiếu, ví dụ: 157>"
disable-model-invocation: true
---

Phiên này đội mũ **executor** cho phiếu `BACKLOG-$ARGUMENTS`
(`.claude/crew/roles.md`).

## Vòng làm việc

1. `scripts/crew new $ARGUMENTS` — nhận cây `../<repo>-b$ARGUMENTS`, làm việc
   TRONG cây đó, đặt tên phiên `<repo>/b$ARGUMENTS`.
2. Đọc phiếu và brief của nó (đã được copy vào cây). Làm **trọn phiếu**: code,
   test, docs, dòng audit — phần nào của phiếu cũng là của bạn, không chuyển
   tay cho vai khác.
3. Phần chạm máy thật (e2e, staging) để **nhỏ và ở cuối**, và khoá trước:
   `scripts/crew lock acquire <resource> $ARGUMENTS` → chạy → `release`.
4. Commit cuối mang trailer:

   ```
   Closes: BACKLOG-$ARGUMENTS
   ```

5. `scripts/crew done $ARGUMENTS` — sáu bước gộp với hai phép kiểm nằm trong
   ruột lệnh. **Không bao giờ gõ tay sáu lệnh đó** (`.claude/crew/worktrees.md`).

## Luật riêng của vai

- **Xanh là gộp, không chờ ai duyệt.** Cổng người duyệt đã được đo trước khi
  bỏ: việc xong nằm chờ 7h18 mà không ai đọc. Điều kiện gộp là typecheck +
  test xanh, và `crew done` tự kiểm điều đó.
- Phiếu hoá ra nặng hơn mức planner xếp (giữ khoá lâu, chạm nhiều tệp hơn
  `scope_files:`) → **báo ngược con số thật cho planner** trước khi làm tiếp.
- Bị chặn bởi thứ chỉ người dùng quyết được → ghi blocker vào phiếu và dừng
  phần đó, không lấn sang phiếu khác trong cùng cây.
