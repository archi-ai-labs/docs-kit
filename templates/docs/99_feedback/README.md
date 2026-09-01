# 99_feedback — chỗ báo lỗi cho chính bộ kit

> Oversight. Thư mục này **không mô tả sản phẩm của repo này**. Nó ghi những chỗ
> docs-kit hoặc crew làm sai, làm thiếu, hoặc bắt trả giá quá đắt.

Mỗi vấn đề là **một file**, và file đó **chính là prompt**: copy nguyên văn rồi
dán vào một phiên làm việc trên repo docs-kit là đủ để người bảo trì bắt tay vào
sửa. Không phải viết lại, không phải tóm tắt, không phải nhớ lại phiên đã đóng.

## 1 · Khi nào phải ghi một file

Ghi khi gặp một trong bốn tình huống dưới đây.

1. **Script hoặc hook làm khác điều chuẩn nói.** Validator báo `FAIL` cho một
   thứ đúng, hoặc im lặng trước một thứ nó khai là có kiểm.
2. **Bạn phải lách kit mới xong một việc bình thường** — sửa tay file sinh tự
   động, bỏ qua một cổng, hoặc chạy một bước không tài liệu nào nhắc tới. Đây là
   tín hiệu mạnh nhất trong bốn cái, vì nó chứng minh cái giá bằng hành động chứ
   không bằng cảm nhận.
3. **Một câu trong `STANDARD.md`, `EXECUTION.md` hay một `SKILL.md` bị repo này
   chứng minh là sai**, hoặc mô tả một thứ không tồn tại.
4. **Bạn cần chỗ ghi một sự thật có thật mà mô hình không có ô nào cho nó.**

## 2 · Khi nào KHÔNG ghi

- **Lỗi của chính bạn mà kit bắt đúng.** Validator chặn một ref sai là nó đang
  làm việc của nó.
- **Vấn đề nằm ở repo này** — code, nội dung tài liệu, quy ước nội bộ. Chỗ của
  nó là một Issue trong `20_issues/`, không phải ở đây.
- **Sở thích mà bạn không nêu được cái giá.** "Tôi thích tên khác" không đủ.
- **Vấn đề đã có file rồi.** Nối một dòng vào mục *Seen again* của file cũ. Số
  lần gặp lại là bằng chứng, còn file thứ hai chỉ là nhiễu.

Một câu kiểm trước khi tạo file: **nếu bạn không nói được kit nên làm khác đi thế
nào, thì chưa đủ để ghi.** Nói với người dùng, đừng tạo file.

## 3 · Tạo file

```bash
bash "$PLUGIN_ROOT/scripts/docs_feedback.sh" new crew-done-merge-order
```

Lệnh này cấp id kế tiếp, sao chép `TEMPLATE.md`, rồi điền sẵn phần bối cảnh mà
người viết hay đoán sai: phiên bản kit, profile của repo, git rev, và nền chạy.
Việc còn lại là điền các mục trong thân file.

Xem những gì đã ghi, và lấy nguyên văn một file để gửi đi:

```bash
bash "$PLUGIN_ROOT/scripts/docs_feedback.sh" list
bash "$PLUGIN_ROOT/scripts/docs_feedback.sh" show 003
```

`$PLUGIN_ROOT` là thư mục cài docs-kit. Trong một phiên Claude Code, biến
`$CLAUDE_PLUGIN_ROOT` đã có sẵn nên agent dùng thẳng. Gõ tay thì lấy bản mới
nhất trong cache, vì cache giữ nhiều phiên bản cùng lúc nên phải sắp xếp chứ
không lấy bừa một cái:

```bash
PLUGIN_ROOT="$(ls -d ~/.claude/plugins/cache/*/docs-kit/*/ | sort -V | tail -1)"
```

## 4 · Vòng đời

| `status` | Nghĩa |
|---|---|
| `open` | đã ghi, chưa gửi cho docs-kit |
| `sent` | đã dán vào một phiên docs-kit; đang chờ |
| `fixed` | đã có bản kit sửa nó — điền phiên bản vào `fixed_in:` |

File ở `fixed` vẫn nằm lại đây. Nó trả lời câu hỏi "vì sao repo này từng làm theo
cách kỳ lạ đó" cho người đọc hai năm sau, và một dòng lịch sử rẻ hơn nhiều so với
một lần điều tra lại.

## 5 · Các trường trong frontmatter

| Trường | Giá trị | Vì sao có |
|---|---|---|
| `about` | `docs-kit` · `crew` | hai nửa của kit có người sửa và nhịp phát hành khác nhau |
| `kind` | `bug` · `doc` · `gap` · `friction` | loại việc phải làm để sửa: code, câu chữ, mô hình, hay chi phí |
| `severity` | `silent` · `blocks` · `friction` | `silent` nặng nhất: kit trả lời sai hoặc bỏ qua một cảnh báo, và **không ai nhìn thấy** |
| `status` | `open` · `sent` · `fixed` | §4 |
| `kit_version` · `rev` · `profile` · `platform` | script điền | một lỗi không tái hiện được thì bối cảnh là thứ duy nhất còn lại |

Không trường nào ở đây kết thúc bằng `_ref`, và đó là chủ đích: một báo cáo phải
sống lâu hơn cái phiếu làm lộ ra nó. Cần nhắc tới một tài liệu thì viết id vào
thân file như một câu bình thường.

## 6 · Validator nhìn thư mục này thế nào

Như mọi thư mục tham chiếu khác: không kiểm frontmatter, không kiểm neo, không
đưa vào `INDEX.md`. Chỗ này ghi lại điều bộ kiểm tra chưa biết cách bắt, nên bắt
nó tự kiểm chính mình sẽ là một vòng lặp vô nghĩa.
