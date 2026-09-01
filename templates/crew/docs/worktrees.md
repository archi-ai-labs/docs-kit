# worktrees — cây, nhánh, và vì sao gộp là một lệnh

## Sinh cây

```
scripts/crew new 157
```

Lệnh này từ chối khi `BACKLOG-157` chưa nằm trong `docs/23_backlog/` (không có
phiếu thì không có cây), tạo `../<repo>-b157` trên nhánh `work/b157` từ nhánh
dev, copy các thư mục dependency khai trong config, và copy `briefs/` nếu có —
vì `briefs/` là thư mục gitignored, một cây mới checkout sẽ không tự có nó.

Hai cái bẫy đã vấp thật mà `crew new` tồn tại để chặn:

1. **Cây mới không có dependency.** Copy từ cây chính mất vài giây; cài lại
   mất lâu hơn nhiều; quên hẳn thì lượt test đầu tiên hỏng ngay.
2. **Đừng để công cụ tự dựng worktree.** Nó tạo thư mục tên ngẫu nhiên, nhánh
   tên ngẫu nhiên, không dependency — và một cây như thế nằm lại ở detached
   HEAD từng làm lệnh gộp fast-forward **nhầm nhánh mà vẫn báo thành công**.

Rộng hơn hai cái bẫy đó: cây checkout chưa phải môi trường làm việc, và
khoảng cách này được đo. Những thứ gitignored — thư mục dependency, repo phụ
lồng bên trong, tệp `.env` — không tự theo cây mới, nên `crew new` đắp lại từ
config: `copy` cho thứ có sửa (dùng APFS clone nên hàng GB chỉ tốn vài giây),
`link` cho thứ chỉ-đọc dùng chung, `setup_cmd` cho phần còn lại, rồi in tổng
thời gian và ghi dòng `SETUP` vào log. Hai luật đi kèm: thời gian dựng cây
lớn hơn phần việc dự kiến thì phiếu thuộc fast-pair hoặc nên gộp phiếu, và
phiếu SỬA một repo lồng thì mở ở crew của chính repo đó, vì cây ngoài không
cô lập được sửa đổi bên trong, còn sửa trên bản copy sẽ chết theo cây.

## Gộp — chạy lệnh, không gõ lại

```
scripts/crew done 157
```

Sáu bước nằm trong ruột lệnh: merge nhánh dev vào cây phiếu (xung đột giải
tại đây), typecheck + test đúng nội dung sắp lên, **kiểm 1** cây chính đang
đúng nhánh dev, **kiểm 2** cây chính sạch (bẩn thì nêu đích danh tệp),
`merge --ff-only`, push, rồi phần đóng phiếu: đọc trailer
`Closes: BACKLOG-157` để chạy docs_close, trả khoá, xoá cây.

Vì sao không gõ tay: thủ tục để dạng văn xuôi sẽ được gõ lại theo trí nhớ, và
hai phép kiểm giữa là thứ rơi trước tiên lúc mệt — trong khi kiểm 1 là "merge
đáp xuống nhánh cây chính ĐANG mở, không phải nhánh bạn nghĩ", và kiểm 2
thường bắt được một fast-pair đang sửa dở. Repo gốc đo lớp lỗi này cắn **5 lần
trong một ngày**.

Executor tự gộp việc đã xanh, không có cổng người duyệt: cổng ấy được đo trước
khi bỏ — việc xong nằm chờ **7h18**, 6h55 và qua đêm, ba lần trong hai ngày,
không ai đọc code trong lúc chờ.

**Giới hạn đã biết, ghi ra để khỏi thành bất ngờ:** cây chính sạch không có
nghĩa là không ai đang đọc nó giữa chừng một lượt review.

## Dọn

`crew done` xoá cây khi xong. Cây mồ côi (còn cây mà phiếu đã done, hoặc cây
không có phiếu) hiện trong `scripts/crew status` — dọn là việc của steward.
