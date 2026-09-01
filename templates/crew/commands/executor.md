---
description: "Vai executor — một phiếu, một cây, làm trọn tới done rồi tự gộp."
argument-hint: "<số phiếu, ví dụ: 157>"
disable-model-invocation: true
---

Phiên này đội mũ **executor** cho phiếu `BACKLOG-$ARGUMENTS`
(`.claude/crew/roles.md`).

## Bước 0 — đúng title, trước mọi việc khác

`scripts/crew name executor $ARGUMENTS`. Xanh thì làm tiếp; đỏ thì đặt lại
title rồi chạy lại. Trong app phiên tự đổi title của chính nó được, ngoài
terminal thì đưa dòng `/rename` mà lệnh in ra cho người dùng.

Nếu bạn được mở từ một task chứ không do người dùng gõ `/executor`: bạn không
**gọi** được tệp vai này, vì mọi tệp vai đều khoá `disable-model-invocation` —
cái mũ do người giao chứ không phải thứ model tự đội. Lấy nội dung nó bằng
`scripts/crew role executor`, đọc từ cây chính nên chạy được cả khi bạn đang
đứng trong cây làm việc.

## Vòng làm việc

1. `scripts/crew new $ARGUMENTS` — nhận cây `../<repo>-b$ARGUMENTS` và làm việc
   TRONG cây đó.
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
