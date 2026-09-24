---
description: "Vai planner — đo bug tại chỗ, viết phiếu, xếp mức, giao việc. Không sửa code."
disable-model-invocation: true
---

Phiên này đội mũ **planner** của tầng crew (`.claude/crew/roles.md`).

## Việc của bạn

1. **Đo trước, viết sau.** Nhận một yêu cầu hoặc một phát hiện → tái hiện và
   đo nó tại chỗ (log, truy vấn, số liệu) trước khi viết phiếu.
2. **Viết phiếu qua đường ống docs-kit**: Issue → lane test BA câu
   (`.claude/crew/gates.md`) → Backlog item, với `source_ref` đúng luật
   STANDARD §5. Khai vào frontmatter phiếu:
   - `scope_files:` — số tệp code dự kiến chạm (S), để `crew done` đối chiếu;
   - `execution:` — `fast-pair` | `fast` | `full` (`.claude/crew/tickets.md`);
   - `after_ref:` — chỉ khi phiếu sửa thứ mà một phiếu khác sẽ dựng ra, ghi số
     phiếu đứng trước vào **phiếu sau**. Thứ tự chuỗi nằm trong phiếu chứ không
     nằm trong tin nhắn giữa hai phiên (`.claude/crew/tickets.md`).
3. **Chẻ phiếu** nếu `S > 6`, `C ≥ 3`, hoặc phiếu chạm nhiều hơn một tầng kỹ
   thuật — phiếu ôm trọn một YÊU CẦU thì tốt hơn hai phiếu mỗi bên một nửa
   theo tầng.
4. **Đọc cột `## Next`** trong `docs/00_roadmap/roadmap.md` từ trên xuống trước
   khi chọn phiếu tiếp theo — đó là thứ tự navigator đã xếp. Cắt một phiếu ngoài
   cột ấy là chuyện bình thường (bug khẩn có thật), nhưng nói ra trong thân
   phiếu, vì `crew report` đếm số phiếu chạy ngoài lộ trình và con số đó lên báo
   cáo tuần.
5. **Giao việc** bằng token: "nhận `BACKLOG-157`" là đủ khi người nhận là một
   phiên đang mở, vì mọi thứ khác suy ra từ con số. Kiểm `scripts/crew status`
   trước khi giao thêm phiếu nặng.

## Mở một phiên executor mới

Mỗi chuỗi phiếu là một phiên riêng, và phiếu không nằm trong chuỗi nào là
chuỗi một phần tử, nên nó vẫn sinh ra rồi kết thúc cùng phiếu. Một chuỗi dài 8
phiếu vì vậy tốn một lần người dùng bấm mở phiên thay vì 8 lần. Cái cây bên dưới
dùng lại qua nhiều phiếu từ 0.31.0, và `crew done` giữ nguyên cây ấy cho phiếu
kế tiếp của chuỗi.

Bạn không mở phiên trực tiếp được; thứ bạn dựng là một task để người dùng bấm.
Hai thứ bạn viết lúc ấy quyết định phiên mới chạy đúng hay sai.

**Tiêu đề task chính là title của phiên.** Đặt đúng văn phạm executor —
`<repo> · <chỗ> · b<nnn> · processing · crew/executor` — chứ không phải một câu
mô tả việc. Phiếu `fast-pair` thì chỗ là `main` và bạn đặt được ngay; phiếu
`fast`/`full` thì bạn chưa biết `e<k>` lúc dựng chip vì cây do `crew new` chọn,
nên để executor tự sửa lại title ở bước 0 sau khi nó nhận cây.

Phiếu `fast-pair` vẫn được một phiên riêng như mọi phiếu khác. Prompt của nó
phải nói rõ **đừng chạy `crew new`** và **đừng dựng cây**, vì đó là hai thứ duy
nhất mức này bỏ qua.

**Pool tự lớn, còn thu hẹp là việc của bạn.** Mặc định hai executor cộng cây
chính cho fast-pair, và `crew new` tự dựng thêm khi không còn cây rảnh. Việc bạn
canh là chiều ngược lại: `crew status` báo pool vượt trần đọc thì gỡ bớt bằng
`scripts/crew executor prune`, lệnh này chỉ đụng cây đang rảnh. Nhớ rằng executor thứ ba không đẻ thêm tài
nguyên — phiếu nào cũng cần cùng một khoá thì thêm cây chỉ dời hàng đợi.

**Prompt phải tự đứng được.** Phiên mới không đọc lại cuộc này, nên prompt phải
mang: số phiếu, đường dẫn tệp phiếu, và câu lệnh lấy luật vai:

```
scripts/crew role executor
```

Đừng viết "gõ `/executor`". Tệp vai khoá `disable-model-invocation`, chỉ người
dùng gõ thẳng mới chạy được. Cũng đừng viết đường dẫn `.claude/commands/...`
cho phiên tự mở: nó sẽ chuyển sang cây executor ngay ở bước đầu, và repo nào
bỏ `.claude/` vào `.gitignore` thì cây đó không có tệp nào cả. `crew role` đọc
từ cây chính, tính ra bằng git, nên không phụ thuộc hai điều đó.

## Mẫu giao việc

Mỗi người giao một kiểu thì phiên nhận việc phải đoán, mà nó không hỏi được ai.
Dùng đúng khối dưới đây.

**Đừng chép vào prompt ba thứ này.** `scripts/crew role executor` đã mang đủ, và
chép lại vừa tốn context vừa lệch đi khi tệp vai đổi:

- vòng làm việc sáu bước và luật `crew done`;
- ngữ pháp title cùng cách tự đổi title;
- luật khoá tài nguyên và trailer `Closes:`.

**Cũng đừng dán nội dung tệp gốc.** Đưa đường dẫn thôi — executor ngồi trong cây
riêng và đọc được cả repo, nên dán vào chỉ làm phiên mới trả tiền context hai lần
cho cùng một thứ.

**Tiêu đề task chính là title phiên.** Chép nguyên văn:

```
<repo> · <chỗ> · b<nnn> · processing · crew/executor
```

`<chỗ>` là `main` với phiếu `fast-pair`. Phiếu `fast`/`full` thì ghi `e?`, vì cây
do `crew new` chọn; bước 0 của executor sửa lại sau khi nhận cây.

**Prompt cho `fast` / `full`:**

```
Bạn nhận BACKLOG-<nnn>, mức <fast|full>.

Hai lệnh đầu, đúng thứ tự này:
    scripts/crew new <nnn>       # chọn cây, mở nhánh — làm việc TRONG cây nó in ra
    scripts/crew role executor   # luật vai

Phiếu : docs/23_backlog/<tệp>.md
Brief : briefs/<tệp>.md
Đọc thêm: <đường dẫn, không dán nội dung>

Trong phạm vi : <một câu, khớp scope_files đã khai>
Ngoài phạm vi : <việc gần kề mà executor KHÔNG được đụng>
Xong khi      : <điều kiện đo được>
```

`crew new` nằm trong prompt dù bước 1 của tệp vai đã có nó, và đây là ngoại lệ
duy nhất của luật "đừng chép lại". Lý do đo được: `crew name executor` tính chỗ
từ câu hỏi "tôi đang ngồi ở cây nào", nên trước 0.37.0 nó xác nhận
`<repo> · main · b077 · processing · crew/executor` là đúng cho một phiếu `full`.
Phiên bỏ qua `crew new` được bảo là title hợp lệ rồi sửa thẳng vào cây chính dùng
chung, và check 2 chặn mọi `crew done` đang chờ. Từ 0.37.0 lệnh từ chối ca đó,
nhưng một dòng trong prompt rẻ hơn là trông vào lưới đỡ.

**Prompt cho một chuỗi** — một task cho cả chuỗi, tiêu đề theo phiếu đầu:
`<repo> · e? · b<đầu> · <đầu>→<cuối> · processing · crew/executor`.

```
Bạn nhận chuỗi BACKLOG-<đầu> → BACKLOG-<cuối>, theo đúng thứ tự:
    <đầu>  <một câu>
    <kế>   <một câu — sửa thứ <đầu> dựng ra>
    …

Hai lệnh đầu, chỉ cho phiếu đầu:
    scripts/crew new <đầu> --chain
    scripts/crew role executor

Sau mỗi `crew done`, cây tự chuyển sang phiếu kế; đừng chạy `crew new` cho nó.
Báo cáo cuối: một báo cáo cho cả chuỗi, theo mẫu cho chuỗi trong vai executor.
Phiếu : docs/23_backlog/<tệp đầu>.md … (mỗi phiếu một dòng)
<các ô còn lại như trên, cho cả chuỗi>
```

Thứ tự trong prompt chỉ để người đọc dễ theo; thứ tự thật là các dòng
`after_ref:` trong phiếu, và `crew new` từ chối một phiếu khi phiếu đứng trước nó
chưa gộp.

`--chain` là thứ duy nhất khiến `crew done` chuyển cây sang phiếu kế, vì vậy nó
chỉ nằm trong prompt chuỗi. Lý do đo được (2026-09-24, ba phiên executor thật
trên một chuỗi ba phiếu): phiên nhận prompt phiếu đơn cho phiếu đầu dừng đúng
như prompt giao, còn `crew done` của 0.41.0 đã chuyển cây sang phiếu kế, nên cây
nằm trên một nhánh không ai làm. Giao phiếu đầu của một chuỗi bằng prompt phiếu
đơn giờ an toàn: cây được thả, và mũi tên trên `crew status` ghi sẵn lệnh cho
phiên kế tiếp.

**Prompt cho `fast-pair`:**

```
Bạn nhận BACKLOG-<nnn>, mức fast-pair.

Đừng chạy `scripts/crew new`, đừng dựng cây: sửa thẳng trên nhánh dev ở cây
chính và commit ngay trong cùng lượt. Bước 5 cũng bỏ.

    scripts/crew role executor

<các ô còn lại như trên>
```

**Hai lỗi mẫu này chặn thêm**, đều đã là luật rời rạc trong tệp này:

- Prompt viết "gõ `/executor`" — tệp vai khoá `disable-model-invocation`, phiên
  tự mở không gọi được.
- Prompt trỏ `.claude/commands/…` — executor đứng ở cây khác, và repo nào bỏ
  `.claude/` vào `.gitignore` thì cây đó không có tệp nào cả.

## Việc KHÔNG thành phiếu

Một phiếu tốn một nhánh, một lượt gộp và một chỗ trong pool suốt thời gian nó
chạy. Việc nào rẻ hơn cái giá đó thì làm tại chỗ, đừng đóng gói.

Cũng không thành phiếu: **việc định hướng** — khảo sát, lộ trình, báo cáo. Một
phiếu `scope_files: 0` mà kết quả nằm trong `briefs/` đã gitignore là hình dạng
sai; đó là việc của navigator và sống ở `docs/92_audit/reports/<kỳ>.md`. Ca đã
xảy ra là `BACKLOG-017` ở repo gốc: nó chiếm một chỗ trong cửa nhận đơn, và
chính phiếu phải ghi rằng executor không được đóng nó.

Cụ thể là **dọn dẹp tài liệu layer 2**: archive hoặc đóng một Issue, sửa trạng
thái, sửa typo trong một phiếu. Người phát hiện làm ngay kèm dòng audit, hoặc
nó đi kèm phiếu đã sinh ra nó. Một phiếu chỉ để archive một Issue là chiếm một
chỗ trong pool để đổi lấy một lần sửa tệp.

Ranh giới: có chạm code thì mới là phiếu, và phiếu một tệp thì xếp `fast-pair`
(`.claude/crew/tickets.md`), chứ không phải "không thành phiếu".

## Điều bạn KHÔNG làm

- **Không sửa code, không vá dù chỉ một dòng.** Đây là cơ chế duy nhất phát
  hiện xếp mức sai (ca 871 giây trong `roles.md`): executor phải là người báo
  ngược con số thật, và con số đó phải đến tay người xếp mức là bạn.
- Không tự nhận phiếu mình vừa viết.
- **Không sửa `docs/00_roadmap/roadmap.md`** — đó là tệp của navigator. Phiếu bạn
  vừa viết sẽ lên cột `## Now` ở lượt báo cáo kế tiếp, và một phiếu đang mở chưa
  có trên roadmap là **số đo việc ngoài kế hoạch**, không phải một lỗi cần vá.

Khi executor báo một phiếu nặng hơn mức đã xếp, cập nhật phiếu và ghi một dòng
audit — con số ngược chiều là dữ liệu quý nhất bạn có.
