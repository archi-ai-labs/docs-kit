# gates — bốn cổng trước khi hỏi người dùng quyết

Vấn đề bốn cổng giải: người dùng gật một quyết định họ chưa hiểu, và cái gật
đó trông giống hệt một cái gật có hiểu biết, kể cả với chính họ.

Tài liệu này giữ phần **luật**. Phần **cách làm** một lời giải thích đạt
chuẩn — ba khuôn hình vẽ, sơ đồ TRƯỚC/SAU, tradeoff kèm số, luật hai phép đo
với ca gốc, luật link id, câu kiểm mức 2 — đóng gói trong skill `explain`: gõ
`/docs-kit:explain <vấn đề>`, hoặc phiên tự nạp nó khi bạn hỏi về một Issue,
Backlog, Proposal, Decision, hay về một cơ chế của chính repo này (một script,
một hook, một skill, một khoá cấu hình).

## Gate 0 — lane test, ba câu (STANDARD §5)

1. Thay đổi này có sửa tài liệu layer 1 không — Architecture, Business logic,
   API contract?
2. Nếu hoá ra sai, revert có mất hơn 1 ngày không?
3. Có thao tác nào **không lùi được** không — xoá dữ liệu, publish ra ngoài,
   bật cờ một chiều, gửi thứ gì đó cho người khác?

"Có" một câu bất kỳ → **full lane**. Câu 3 thắng hai câu kia: rollback trong
5 phút không cứu được dữ liệu đã biến mất.

"Không" cả ba → **fast lane**, và phiên phải khai điều đó ra bằng một dòng
marker ở đầu dòng, kèm lý do:

```
LANE: fast — <lý do>
```

Hook explain-gate tìm đúng dòng này (hoặc một lời gọi công cụ vẽ) trong các
trả lời của lượt hiện tại trước khi phiên được hỏi người dùng chọn.

## Gate 1 — giải thích

| Việc | Phải có |
|---|---|
| mọi quyết định full lane | sơ đồ TRƯỚC/SAU, tradeoff hai chiều **kèm số** |
| làm UI | vẽ nháp đưa xem TRƯỚC khi viết code |
| đổi flow backend / schema | sơ đồ flow trước và sau, TRƯỚC khi sửa |

Kèm hai luật con mà skill `explain` mang ca gốc và cách làm: mọi id nhắc tới
phải là link trỏ tệp kèm một câu nó là gì, và mọi con số chống đỡ một thao
tác không lùi được cần **hai phép đo độc lập**, trong đó phép thứ hai phải có
khả năng chứng minh con số SAI.

## Gate 2 — xác nhận hiểu, bắt buộc mức 2

| Mức | Hình dạng | Bắt được lỗi của ai |
|---|---|---|
| 0 | họ nói "ok, hiểu rồi" | không ai |
| 1 | họ nhắc lại bằng lời của họ | của họ |
| 2 | **phiên hỏi ngược một câu kiểm** chỉ trả lời đúng được nếu đã nắm mô hình | của **cả hai** |

Ghi lại **mức** xác nhận, đừng chỉ ghi "đã xác nhận". Im lặng hoặc trả lời mơ
hồ đọc là CHƯA hiểu: dừng lại, không đưa lựa chọn.

## Gate 3 — bây giờ mới hỏi

Đưa lựa chọn ra, không sớm hơn, và bốn cổng không gộp làm một. Trả lời ngắn
áp cho báo cáo; nó KHÔNG áp cho phần giải thích đứng trước một quyết định.
