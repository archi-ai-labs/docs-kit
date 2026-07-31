---
id: PROPOSAL-000
issue_ref: ISSUE-000
problem: "Log đang là text thuần không cấu trúc; debug xuyên service phải nối grep rất mong manh"
proposed: "Dùng JSON-lines với bộ trường dùng chung (ts, level, service, trace_id, msg)"
impact: "none"
---

# PROPOSAL-000 — Example: structured logging format

> Thuộc chuỗi ví dụ `-000`. Xem `20_issues/ISSUE-000-example.md`.

## Problem

Nêu lại vấn đề từ Issue, kèm bằng chứng mới thu được trong lúc tìm hiểu.

## Alternatives considered

1. **JSON-lines với bộ trường dùng chung (phương án đề xuất)** — máy đọc được ở mọi
   nơi; đánh đổi: người đọc log thô thấy hơi rối.
2. **logfmt (`key=value`)** — dễ đọc cho người hơn; đánh đổi: hỗ trợ dữ liệu lồng
   nhau yếu, ít parser sẵn có trong stack của mình.
3. **Giữ text thuần + siết quy ước** — không tốn chi phí migrate; đánh đổi: không
   giải quyết được chuyện máy parse, tức vấn đề gốc vẫn còn nguyên.

## Proposed option

Phương án 1. Triển khai qua một logging helper dùng chung; các service migrate dần
từng chỗ gọi, sau cùng một interface.

## Impact on Architecture / Roadmap

Không — không đụng ranh giới component, không đụng roadmap (`impact: none` phía
trên). Nếu một proposal có ảnh hưởng thật, phải mô tả chính xác cái gì sẽ bị sửa.
