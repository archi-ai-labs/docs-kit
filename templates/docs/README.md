# docs/ — tài liệu ba lớp

Bộ khung do docs-kit tạo. Chuẩn đầy đủ: `STANDARD.md` của docs-kit. Đọc file này
trước — mất 30 giây.

## 1 · Layers

| Layer | Thư mục | Bản chất | Luật sửa |
|---|---|---|---|
| 1 · Foundation | `00_roadmap` `01_products` `02_architecture` `03_business-logic` `04_api` | Trạng thái | **Chỉ** đổi qua một Decision đã duyệt (`amended_by`) |
| 2 · Change | `20_issues` `21_proposals` `22_decisions` `23_backlog` | Tiến trình, truy nguyên được | Theo đúng luồng bên dưới |
| 3 · Reference | `30_conventions` `40_services` `50_runbooks` `60_fe-integration` `70_deploy` `93_qa` | Tài liệu vận hành | Sửa thẳng, không cần Decision |
| Oversight | `92_audit` | Nhật ký chỉ ghi thêm | Chỉ nối dòng, không bao giờ viết lại |
| Oversight | `99_feedback` | Lỗi của chính docs-kit / crew | Mỗi vấn đề một file, file đó là prompt gửi đi |

## 2 · Flow

```
Issue (exploring → open)
  ├─ FAST lane ──────────────────────────────► Backlog (source_ref = Issue)
  └─ FULL lane ──► Proposal ──► Decision ────► Backlog (source_ref = Decision)
Decision được duyệt ⇒ sửa 02_architecture / 03_business-logic / 04_api NGAY trong phiên đó (+ amended_by)
Backlog item xong   ⇒ status: done + nối một dòng vào 92_audit/
Review (định kỳ)    ⇒ read-only trên layer 1–2; phát hiện nối vào 92_audit/
```

## 3 · Lane test — ba câu hỏi, "có" một câu ⇒ FULL lane

1. Thay đổi này có sửa Architecture, Business logic hay API contract không?
2. Nếu hoá ra sai, rollback có mất hơn 1 ngày không?
3. Có thao tác nào không lùi được không — xoá dữ liệu, publish ra ngoài, bật cờ
   một chiều, gửi thứ gì đó cho người khác? Câu này thắng hai câu kia: rollback
   5 phút không cứu được dữ liệu đã mất.

## 4 · Folders

| # | Thư mục | Để làm gì (một dòng) |
|---|---|---|
| 00 | `00_roadmap` | Sản phẩm đang đi về đâu: now / next / later |
| 01 | `01_products` | Mỗi sản phẩm là gì, cho ai, thế nào là thành công |
| 02 | `02_architecture` | Component, lược đồ dữ liệu (```erd```), type (```class```), luồng dữ liệu, stack, ràng buộc — chỉ sửa qua Decision |
| 03 | `03_business-logic` | Quy tắc rẽ nhánh (```flowchart```) + vòng đời entity (```state```) — chỉ sửa qua Decision |
| 04 | `04_api` | Contract ở ranh giới (```api```): operation nào tồn tại, nghĩa là gì, cố ý KHÔNG expose cái gì. `service:` phải trùng một component. Chỉ sửa qua Decision |
| 20 | `20_issues` | Mọi thứ đáng làm đều vào đây trước (nghiên cứu thô bắt đầu ở `exploring`) |
| 21 | `21_proposals` | Phương án cho full lane, kèm lựa chọn thay thế + đánh đổi |
| 22 | `22_decisions` | Duyệt / loại, do ai, vì sao |
| 23 | `23_backlog` | Việc làm được ngay, truy nguyên qua `source_ref` |
| 30 | `30_conventions` | Quy ước code / đặt tên / quy trình |
| 40 | `40_services` | Tra cứu service: cái gì chạy ở đâu, ai quản |
| 50 | `50_runbooks` | Quy trình vận hành từng bước |
| 60 | `60_fe-integration` | Contract và ghi chú cho tích hợp frontend |
| 70 | `70_deploy` | Ship kiểu gì: môi trường, pipeline, rollback |
| 92 | `92_audit` | Nhật ký chỉ ghi thêm — nơi tra cứu truy nguyên |
| 93 | `93_qa` | Chiến lược test, checklist QA, chỗ còn hổng |
| 99 | `99_feedback` | Chỗ duy nhất trong `docs/` không nói về sản phẩm: những chỗ docs-kit hoặc crew làm sai — xem §10 |

## 5 · Traceability

`92_audit/` là chỗ tra *chuyện gì đã xảy ra, dưới Decision/Backlog nào, và lệch ra
sao*. Chỉ ghi thêm — được đối chiếu với lịch sử git.

Id (`ISSUE-`, `PROPOSAL-`, `DECISION-`, `BACKLOG-` + số 3 chữ số) nằm ở `id:` trong
frontmatter; mọi `*_ref:` đều trỏ tới một id, **không bao giờ trỏ tới tên file**.
Bốn file `*-000` đi kèm là một chuỗi ví dụ chạy được — xoá cả bốn cùng lúc, hoặc
giữ lại làm mẫu định dạng. Id thật bắt đầu từ `001`.

Tài liệu không còn đổi được nữa thì chuyển vào `_archive/` ngay trong thư mục của nó
(Backlog `done` đã có dòng audit, Issue `archived`, chuỗi đã khép). Mọi điều kiện ở
đây đều là vị từ trên frontmatter nên script quyết định được: chạy
`docs_close.sh --archive --apply .`, và nó dùng `git mv` để lịch sử đi theo file.
Việc này **chỉ giảm chi phí đọc, không giảm chuẩn**: validator vẫn kiểm đủ, ref vẫn
phân giải, `INDEX.md` vẫn liệt kê kèm tiền tố `_archive/`.

## 6 · Đọc thế nào cho rẻ

`INDEX.md` (sinh tự động) là **read model cho agent**: mỗi tài liệu một dòng — id,
status, ref, file, mô tả. Đọc nó trước rồi chỉ mở đúng id cần. **Đừng bao giờ glob cả
`22_decisions/` hay `23_backlog/`** — cách đó tốn nguyên một file cho mỗi tài liệu và
chỉ đắt thêm theo thời gian, trong khi câu trả lời thì không dài ra.

`MAP.tsv` (cũng sinh tự động) trả lời câu hỏi ngược lại: **file code này đang được
tài liệu nào mô tả**. Mỗi dòng gồm đường dẫn, tài liệu, thứ trong tài liệu nhận nó, và
`verified_at`. Không tài liệu nào khai thêm gì cho file này — nó gom lại đúng những
neo vốn đã nằm trong markdown. Stop hook đọc nó để biết một file vừa sửa có ai mô tả
không, nên file nào không ai nhận thì hook im lặng.

Ba file HTML (`index.html`, `current.html`, `changes.html`) là read model cho người.
Cả năm đều sinh lại bằng `/docs-kit:docs-render`; markdown vẫn là nguồn sự thật.

**`INDEX.md` cũ nguy hiểm hơn `INDEX.md` không có**, vì agent tin nó. `MAP.tsv` cũ còn
khó thấy hơn: nó không tạo cảnh báo sai mà làm cảnh báo **biến mất**, và một phiên
lặng lẽ trông hệt như một phiên sạch. Vì vậy cả hai đều có cổng chặn — đặt dòng này
vào CI cạnh validator:

```bash
docs_render.sh --check .
```

Không ghi gì, dựng lại cả hai bằng đúng code path của render thật nên không thể lệch.
`0` = đang khớp · `1` = thiếu hoặc cũ · `2` = không có `docs/`. Chỉ hai file text kiểm
được kiểu này; ba trang HTML có dấu thời gian nên lần render nào cũng khác.

## 7 · Đồng bộ với code

Mọi fact quan trọng ở layer 1 đều mang một **neo** vào source: component có
`` `path/in/repo` ``, mỗi khối hình có header `code:`. Validator kiểm hai thứ:

- `NOTE [anchor]` — đường dẫn không còn tồn tại. Chắc chắn sai, nhưng là link sai
  chứ không phải tên sai, nên validator in ra và vẫn cho qua (xem §8).
- `NOTE [stale]` — `verified_at` là git rev của lần cuối thực sự đọc code đó; file đã
  đổi kể từ rev ấy. **Cảnh báo, không phải lỗi** — đổi không đồng nghĩa sai.

Đọc lại code xong thì đẩy `verified_at` lên `git rev-parse --short HEAD`. Đây là thứ
biến việc rà soát từ "nhớ thì làm" thành "có nguyên nhân mới làm".

Một neo có thể là danh sách nhiều đường dẫn cách nhau bằng dấu phẩy (chỉ trong header
`code:`), hoặc một glob như `lib/validators/*.schema.ts` — mười bốn schema anh em là
một sự thật về codebase, không phải mười bốn sự thật. `*` và `?` là ký tự đại diện,
còn `[` thì không: `app/users/[id]/page.tsx` là thư mục Next.js có thật.

Khi commit hoàn thành một Backlog item, viết trailer `Closes: BACKLOG-012` vào thông
điệp commit. `docs_close.sh --apply .` sẽ lật `status: done` và ghi dòng audit trích
đúng sha. Dòng audit khi đó dẫn về một commit kiểm được nhiều năm sau, thay vì dẫn về
một phiên chat đã biến mất.

Riêng `04_api/` còn một neo mạnh hơn: `generated_from:` trỏ tới artifact repo tự sinh
(`openapi.json`, `*.proto`). `docs_render.sh --check-api .` so contract với artifact và
báo hai loại lệch — operation **đang chạy mà không ai mô tả** (đúng trigger §6, phát hiện
sau khi việc đã rồi) và operation **mô tả rồi mà artifact không có**. Nửa sinh tự động
không ai bảo trì, nên nó không thể cũ.

## 8 · Validator: tên sai là lỗi, link sai là ghi chú

Validator chạy ở hai mức. Ở mức mặc định, nó chỉ báo `FAIL` khi một **cái tên** sai,
còn mọi liên kết hỏng đều in ra dưới dạng `NOTE` và vẫn thoát 0.

Ranh giới này không nằm ở mức quan trọng mà nằm ở chi phí phát hiện. Một `id:` trùng
làm mọi tham chiếu tới nó trở nên nhập nhằng, và không tham chiếu nào trông có vẻ
sai, nên sẽ không ai nhận ra nữa. Còn một `*_ref:` trỏ vào khoảng không thì chỉ hỏng
đúng một cạnh, và người đầu tiên bấm vào là thấy ngay.

| Mức | Kiểm gì |
|---|---|
| `FAIL` | `id:` thiếu hoặc trùng; tiền tố `id:` không khớp thư mục; enum `lane`/`status`/`outcome` sai; một component name khai ở hai tài liệu với **hai đường dẫn khác nhau**; `92_audit/` bị sửa dòng cũ; token lạ trong `owns` |
| `NOTE` | `*_ref:` rỗng hoặc không phân giải được; Backlog thiếu `source_ref`; thiếu một trường bắt buộc khác `id`; Proposal thiếu mục "Alternatives considered"; `amended_by` trích một Decision không tồn tại; một neo trỏ vào đường dẫn không còn |

Nhắc lại một component name mà không kèm đường dẫn riêng thì không bị báo, vì một tài
liệu flow xuyên suốt buộc phải nhắc lại các thành phần mà `architecture.md` đã khai.

Thêm cờ `--strict` thì mọi dòng ở hàng `NOTE` quay lại thành `FAIL`. Đó là mức dành
cho CI, còn mức mặc định dành cho lúc đang làm việc.

## 9 · Ngôn ngữ

Khung tiếng Anh, giải thích tiếng Việt. Tên thư mục, tên trường frontmatter, giá
trị enum (`open`, `in-progress`, `done`, `approved`, `rejected`, `fast`, `full`),
tiền tố id, tiêu đề mục, và các thuật ngữ (Issue, Proposal, Decision, Backlog,
Architecture, fast lane, full lane) giữ nguyên tiếng Anh — đổi chúng là hỏng
validator. Phần diễn giải viết tiếng Việt, để thuật ngữ Anh nằm trần trong câu.

## 10 · Khi chính bộ kit sai

Mọi thư mục ở trên mô tả sản phẩm, riêng `99_feedback/` mô tả **công cụ**. Ghi một
file vào đó khi script hoặc hook làm khác điều chuẩn nói, khi phải lách kit mới
xong một việc bình thường, khi một câu trong tài liệu của kit bị chứng minh là
sai, hoặc khi cần ghi một sự thật mà mô hình không có ô nào cho nó.

```bash
bash "$PLUGIN_ROOT/scripts/docs_feedback.sh" new <slug>   # tạo phiếu, tự điền bối cảnh
bash "$PLUGIN_ROOT/scripts/docs_feedback.sh" show <id>    # in nguyên văn để gửi đi
```

File tạo ra **chính là prompt**: copy toàn bộ, dán vào một phiên làm việc trên
repo docs-kit là xong. Luật đầy đủ — bốn trường hợp phải ghi và bốn trường hợp
không được ghi — nằm ở `99_feedback/README.md`.

Vấn đề của **repo này** thì không thuộc về đây; chỗ của nó là một Issue trong
`20_issues/`.

Kiểm tra cấu trúc bất cứ lúc nào: `/docs-kit:docs-check` · Đối chiếu sau một phiên
làm việc: `/docs-kit:docs-sync`
