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

Hook explain-gate tìm đúng dòng này trong các trả lời của lượt hiện tại trước
khi phiên được hỏi người dùng chọn. Hook cũng chấp nhận một hình vẽ thay cho
dòng marker, cụ thể là một lời gọi công cụ vẽ hoặc một tệp hình (HTML, SVG,
ảnh) gửi cho người dùng dạng render. Trong tab Code của app desktop, lời giải
thích nằm trọn trong một tệp HTML như vậy, và skill `explain` có sẵn khuôn mẫu.

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
| 2 | **phiên hỏi ngược 1–3 câu kiểm**, mỗi câu chỉ trả lời đúng được nếu đã nắm mô hình | của **cả hai** |

**Từ 1 đến 3 câu, mỗi câu một thay đổi cốt lõi (0.42.3).** Mỗi câu kiểm hỏi về
một thay đổi trong chu trình hoặc trong code mà lời giải thích mang theo, và
thay đổi quan trọng nhất được hỏi trước. Một thay đổi thì một câu; nhiều thay
đổi thì tối đa ba câu, chọn theo mức quan trọng. Đừng hỏi chi tiết bên lề, vì
nó không xác nhận được điều mà quyết định dựa vào.

**Hỏi bằng AskUserQuestion, dẫn người đọc tới đáp án chứ không đánh đố.** Các
câu kiểm nằm trong một lệnh gọi AskUserQuestion, không phải những dòng cuối
chat. Các lựa chọn là những cách hiểu thật của mô hình: cách hiểu đúng, và một
hai cách hiểu sai mà hình vẽ có thể gây ra. Câu nào cũng có một lựa chọn "Chưa
chắc" ghi rõ mục cần đọc lại. Trang HTML lặp lại từng câu hỏi và có sẵn đáp án,
nhưng đáp án được gập lại, bấm mới hiện. Đáp án nói rõ người đọc dễ sai ở đâu và
vì sao, mỗi lựa chọn sai một dòng.

Ghi lại **mức** xác nhận, đừng chỉ ghi "đã xác nhận". Im lặng, chọn "Chưa chắc"
hoặc trả lời mơ hồ đọc là CHƯA hiểu: giải thích lại mục đó, không đưa lựa chọn.
Cổng 2 chỉ đóng khi mọi câu đều được trả lời đúng.

## Gate 3 — bây giờ mới hỏi

Đưa lựa chọn ra, không sớm hơn, và bốn cổng không gộp làm một. Trả lời ngắn
áp cho báo cáo; nó KHÔNG áp cho phần giải thích đứng trước một quyết định.
