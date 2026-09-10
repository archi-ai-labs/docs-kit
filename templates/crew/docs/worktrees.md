# worktrees — pool executor, nhánh, và vì sao gộp là một lệnh

## Pool executor

```
scripts/crew executor add
```

Lệnh này dựng `../<repo>-e1` ở HEAD tách rời trên nhánh dev, rồi đắp lại những
thứ gitignored mà một cây checkout mới không có. Pool mặc định là hai executor,
cộng cây chính dành cho fast-pair.

Cây sống lâu hơn phiếu, còn nhánh và phiên thì không. Trước 0.31.0 cây mang số
phiếu nên phải dựng rồi xoá mỗi phiếu; repo gốc đo được 4 cây cho 15 phiếu, tổng
49 giây dựng. Con số ấy nhỏ ở repo này, nhưng nó bị vứt đi rồi trả lại từ đầu ở
mỗi phiếu, và nó lớn dần theo độ nặng của repo.

## Nhận phiếu

```
scripts/crew new 157
```

Lệnh từ chối khi `BACKLOG-157` chưa nằm trong `docs/23_backlog/` (không có phiếu
thì không có nhánh), tìm executor đang rảnh, rồi mở `work/b157` từ nhánh dev ngay
trong cây đó.

**Không còn cái nào rảnh thì lệnh tự dựng thêm một executor**, vì cỡ pool là một
con số đoán và không nên để nó chặn một phiếu. Lần dựng thêm được ghi dòng `GROW`
vào log, và vượt trần đọc thì lệnh cảnh báo chứ không từ chối.

Thu hẹp lại là việc có chủ ý, và phải gọn trong một lệnh, nếu không thì cái bánh
cóc chỉ quay được một chiều. `scripts/crew executor prune [sàn]` gỡ các cây đang
rảnh xuống tới sàn (mặc định 2) và giữ nguyên mọi executor còn đang ôm nhánh,
kèm gọi tên chúng ra. `scripts/crew executor rm <k>` gỡ đúng một cái, và từ chối
khi cái đó còn giữ nhánh.

**Cây chính đứng ở nhánh nào thì `crew done` gộp vào đó.** Đây là lý do lệnh có
check 1, và cũng là lý do `scripts/crew status` in nhánh của cây chính ngay dòng
đầu: đứng nhầm nhánh thì mọi lượt gộp đều bị từ chối, mà trước 0.36.0 chỉ lúc
chạy gộp mới biết. Bảng còn đếm cây chính đi trước hay sau nhánh dev bao nhiêu
commit, nên nhìn mắt là thấy đã đồng bộ hay chưa.

**Cái ghim phiếu ↔ executor là nhánh đang checkout**, không phải một tệp
registry. Git đã lưu sẵn quan hệ đó, và git cấm hai cây cùng mở một nhánh, nên
không tệp nào cãi lại được. Executor rảnh nằm ở HEAD tách rời, bởi "đứng trên
dev" là thứ duy nhất cây thứ hai không được phép.

**Đừng để công cụ tự dựng worktree.** Nó tạo thư mục tên ngẫu nhiên, nhánh tên
ngẫu nhiên, không dependency, và một cây như thế nằm lại ở detached HEAD từng
làm lệnh gộp fast-forward **nhầm nhánh mà vẫn báo thành công**.

Cây checkout chưa phải môi trường làm việc, nhưng pool trả khoản đó đúng một
lần: `copy` cho thứ có sửa (dùng APFS clone nên hàng GB chỉ tốn vài giây),
`link` cho thứ chỉ-đọc dùng chung, `setup_cmd` cho phần còn lại, và dòng `SETUP`
trong log ghi tên executor chứ không ghi số phiếu.

Khoản tiết kiệm là phiếu vừa xong để lại dependency cho phiếu sau, và đó cũng
là rủi ro mới: phiếu nào đổi lockfile sẽ khiến phiếu kế tiếp test trên cây sai.
Vì vậy `crew new` chạy lại `setup_cmd` khi một tệp trong `resetup_when` khác với
lúc executor được dựng, và bỏ qua khi không tệp nào đổi.

Một ranh giới là luật chứ không phải tính năng thiếu: phiếu **sửa** một repo
lồng thì mở ở crew của chính repo đó, vì executor không cô lập được sửa đổi bên
trong, còn sửa trên bản copy thì không nằm trên nhánh.

## Gộp — chạy lệnh, không gõ lại

```
scripts/crew done 157
```

Sáu bước nằm trong ruột lệnh: merge nhánh dev vào executor đang giữ `work/b157`
(xung đột giải tại đó), typecheck + test đúng nội dung sắp lên, **kiểm 1** cây
chính đang đúng nhánh dev, **kiểm 2** cây chính sạch (bẩn thì nêu đích danh
tệp), `merge --ff-only`, push, rồi phần đóng phiếu: đọc trailer
`Closes: BACKLOG-157` để chạy docs_close, trả khoá, thả executor.

Vì sao không gõ tay: thủ tục để dạng văn xuôi sẽ được gõ lại theo trí nhớ, và
hai phép kiểm giữa là thứ rơi trước tiên lúc mệt — trong khi kiểm 1 là "merge
đáp xuống nhánh cây chính ĐANG mở, không phải nhánh bạn nghĩ", và kiểm 2 thường
bắt được một fast-pair đang sửa dở. Repo gốc đo lớp lỗi này cắn **5 lần trong
một ngày**.

Executor tự gộp việc đã xanh, không có cổng người duyệt: cổng ấy được đo trước
khi bỏ — việc xong nằm chờ **7h18**, 6h55 và qua đêm, ba lần trong hai ngày,
không ai đọc code trong lúc chờ.

**Giới hạn đã biết, ghi ra để khỏi thành bất ngờ:** cây chính sạch không có
nghĩa là không ai đang đọc nó giữa chừng một lượt review.

## Ba trạng thái, đọc từ git

`scripts/crew status` không lưu trạng thái ở đâu cả, nó suy ra từ nhánh và từ
những file chưa commit trong cây:

| Trạng thái | Đọc thế nào | Nghĩa là |
|---|---|---|
| `idle` | HEAD tách rời **và** cây sạch | sẵn sàng nhận phiếu |
| `unclean` | HEAD tách rời nhưng còn file chưa commit | không giữ phiếu nào, nhưng chưa rảnh |
| `processing` | đang giữ `work/b<nnn>` | phiếu đang mở trong executor đó |
| `finishing` | commit trên nhánh đã mang `Closes: BACKLOG-<nnn>` **và** cây sạch | việc khai là xong, chỉ còn thiếu lượt gộp |

Hai chữ **và** trong bảng là kết quả đo ngày 2026-09-09, từ cùng một nguyên
nhân là đọc cây chỉ qua nhánh. Khi trailer đã viết mà còn một file chưa commit,
bảng in ra `finishing dirty=1` — hai cột nói ngược nhau — rồi `crew done` vẫn
chạy trọn: nhánh được gộp, phiếu lật sang `status: done` kèm dòng audit trích
sha, còn file kia không bao giờ rời khỏi executor. Ở đầu kia của vòng đời, một
cây được park bằng tay vẫn mang file thừa của phiếu cũ, đọc ra `idle`, và phiếu
tiếp theo được giao thẳng vào đó.

Vì vậy một cây `unclean` **rơi khỏi pool**: `crew new` dựng thêm executor chứ
không nhận nó, và bạn phải commit hoặc xoá những file được gọi tên thì cây mới
quay lại `idle`.

Phiên `fast-pair` đọc hai trạng thái `processing` và `finishing`, chỉ khác chỗ
tìm: nó không có nhánh riêng nên trailer được tìm thẳng trên nhánh dev. Luật
"cây sạch" **không** áp cho nó, vì cây chính là của chung và chính `crew done`
để lại thay đổi chưa commit ở đó sau mỗi lượt.

Chỉ trạng thái nào có người phản ứng lại mới được đặt tên. `finishing` xứng đáng
vì repo gốc đo được việc xong nằm chờ **7h18** mà không bảng nào nói ra, và phản
ứng đúng là chạy `crew done`. Một trạng thái thứ tư kiểu "đã nhận, chưa bắt đầu"
đã được cân nhắc rồi bỏ, vì nó là một khoảng thời gian chứ không phải một điều
kiện, và không ai hành xử khác đi khi gặp nó.

Hai giới hạn ghi thẳng ra. Số `dirty=` không đếm phần crew tự đắp vào, vì có thứ
không thể gitignore được (luật `thư-mục/` không khớp một symlink) nên đếm vào là
báo sai ngay lúc cây vừa dựng. Và bảng đọc git chứ không đọc phiên, nên nó không
phân biệt được executor đã có phiên mở với executor mà chip chưa ai bấm — điều
này không phải lỗ hổng, bởi `crew new` do chính phiên executor chạy ở bước 1, nên
chip chưa bấm nghĩa là chưa nhận phiếu và bảng đọc `idle` là đúng.

## Thả và dọn

`crew done` thả executor bằng cách tách HEAD về nhánh dev, giữ nguyên phần đã
cấp phát, nên phiếu sau không phải cài lại. Còn tệp lạ mà crew không đắp vào thì
lệnh không thả, mà gọi tên tệp ra, đúng như bản cũ từ chối xoá cây.

Executor mồ côi (đang giữ nhánh của phiếu đã done, hoặc giữ nhánh không có
phiếu) hiện trong `scripts/crew status`. Bỏ bớt một chỗ là
`scripts/crew executor rm <k>`, và lệnh này từ chối khi executor còn giữ nhánh.
