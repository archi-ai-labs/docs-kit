---
description: "Vai executor — một phiếu, một nhánh, làm trọn tới done rồi tự gộp."
argument-hint: "<số phiếu, ví dụ: 157>"
disable-model-invocation: true
---

Phiên này đội mũ **executor** cho phiếu `BACKLOG-$ARGUMENTS`
(`.claude/crew/roles.md`).

## Bước 0 — đúng title, trước mọi việc khác

Chạy `scripts/crew new $ARGUMENTS` (bước 1) trước, vì title cần biết bạn ngồi ở
cây nào; rồi `scripts/crew name executor` ngay sau đó. Xanh thì làm tiếp; đỏ thì
đặt lại title rồi chạy lại.

Title có ba phần lệnh tự đọc từ git, bạn không truyền gì cả:
`<repo> · e1 · b157 · processing · crew/executor` — cây bạn ngồi, nhánh bạn mở,
và trạng thái. Phiên sinh ra ở `processing`, và **đổi sang `finishing` ngay khi
bạn viết commit mang trailer** (bước 4), nên chạy lại lệnh này một lần nữa ở đó. Trong app phiên tự đổi title của chính nó được, ngoài
terminal thì đưa dòng `/rename` mà lệnh in ra cho người dùng.

Nếu bạn được mở từ một task chứ không do người dùng gõ `/executor`: bạn không
**gọi** được tệp vai này, vì mọi tệp vai đều khoá `disable-model-invocation` —
cái mũ do người giao chứ không phải thứ model tự đội. Lấy nội dung nó bằng
`scripts/crew role executor`, đọc từ cây chính nên chạy được cả khi bạn đang
đứng trong cây của executor.

## Vòng làm việc

1. `scripts/crew new $ARGUMENTS` — phiếu rơi vào executor rảnh trên nhánh
   `work/b$ARGUMENTS`; làm việc TRONG cây mà lệnh in ra. Không còn cây rảnh thì
   lệnh tự dựng thêm một executor, nên bạn không bao giờ bị chặn ở bước này.

   **Phiếu khai `execution: fast-pair` thì bỏ qua bước 1 này.** Lệnh sẽ từ chối
   và nói lý do: bạn sửa thẳng trên nhánh dev ở cây chính, commit ngay trong
   cùng lượt, không dựng cây và không mở nhánh. Bước 5 cũng bỏ — phiếu fast-pair
   đóng bằng trailer, `crew done` không tham gia.
2. Đọc phiếu và brief của nó (`briefs/` đã nằm sẵn trong executor). Làm **trọn phiếu**: code,
   test, docs, dòng audit — phần nào của phiếu cũng là của bạn, không chuyển
   tay cho vai khác.
3. Phần chạm máy thật (e2e, staging) để **nhỏ và ở cuối**, và khoá trước:
   `scripts/crew lock acquire <resource> $ARGUMENTS` → chạy → `release`.
4. Commit cuối mang trailer:

   ```
   Closes: BACKLOG-$ARGUMENTS
   ```

4b. `scripts/crew name executor` lần nữa — trailer vừa đẩy trạng thái sang
   `finishing`, và title cũ giờ đã sai. Nếu lệnh vẫn đọc ra `processing` thì cây
   còn file chưa commit; đó là điều kiện của `finishing`, không phải lỗi.
    **Đây là bước bị quên nhiều nhất.** Bảng `crew status` không sao cả vì nó
    tính trạng thái từ git, nhưng *danh sách phiên* thì đọc title, nên một title
    cũ báo cho người ngoài rằng việc vẫn đang chạy. Từ 0.37.0 có hook Stop nhắc
    lúc phiên dừng, kèm sẵn dòng `/rename` — nhưng nhắc là lưới đỡ, không phải
    lịch trình.

5. `scripts/crew done $ARGUMENTS` — sáu bước gộp với ba phép kiểm nằm trong
   ruột lệnh. **Không bao giờ gõ tay sáu lệnh đó** (`.claude/crew/worktrees.md`).
   Check 0 chặn ngay từ đầu nếu cây của bạn còn file chưa commit, vì thứ được
   gộp phải đúng bằng thứ bạn đang có.

6. **Báo cáo cuối** theo mẫu dưới đây, đúng năm mục và đúng thứ tự ấy. Đây là
   thứ duy nhất người giao việc đọc được mà không phải mở repo.

## Mẫu báo cáo cuối

Số ở mục 1, 3, 4 lấy từ thứ máy đã đo, đừng gõ lại theo trí nhớ: sha và trailer
từ commit, thời gian giữ khoá từ dòng `released lock` mà `crew done` in ra.

`declared=`/`actual=` **không** nằm trong output của `crew done`: lệnh ghi nó
xuống nhật ký chứ không in ra màn hình. Lấy bằng:

```
grep "BACKLOG-<nnn>" ../<repo>-crew/log.tsv
```

`<base>` là gốc URL của repo, lấy bằng lệnh chứ đừng gõ tay:

```
git remote get-url origin \
  | sed -e 's|\.git$||' -e 's|.*[:/]\([^/][^/]*/[^/][^/]*\)$|https://github.com/\1|'
```

Lệnh này giả định remote là GitHub. Repo dùng máy chủ khác, hoặc chưa có remote
(`crew done` báo `push skipped`), thì để sha dạng chữ thường — một liên kết sai
tệ hơn không có liên kết.

````
## BACKLOG-<nnn> — <một câu việc đã làm>

**1. Việc đã làm**

| Việc | Tệp chạm | Kết quả |
|---|---|---|
| <việc 1> | [path/a.ts:88](path/a.ts:88) | <xong / một phần> |

**2. Luồng đổi thế nào**

```flow
title: trước
a -> b : <bước cũ>
```

```flow
title: sau
a -> c : <bước mới>
c -> b : <bước thêm>
```

Luồng không đổi thì bỏ hai khối vẽ, viết một dòng:
`Luồng không đổi — chỉ sửa trong một bước sẵn có.`

**3. Bằng chứng**

| Loại | Xem ở đâu | Kết quả |
|---|---|---|
| Commit | [`<sha ngắn>`](<base>/commit/<sha>) | mang trailer `Closes: BACKLOG-<nnn>` |
| Kiểm thử | [<tệp test>](<đường dẫn>) | <n passed, m failed> |
| Phạm vi | dòng `SIZE` trong `../<repo>-crew/log.tsv` | khai `<S>` · thật `<N>` tệp |
| Khoá | `<tài nguyên>` | giữ `<n>`s |

**4. Git**

| | |
|---|---|
| Nhánh | [`work/b<nnn>`](<base>/tree/work/b<nnn>) — hoặc "không có, phiếu `fast-pair`" |
| Gộp vào | [`<dev_branch>` @ `<sha>`](<base>/commit/<sha>) |
| PR | không có — crew gộp thẳng, luồng này không dùng PR |
| Lên prod | **chưa** — `<prod_branch>` chưa đụng, release là việc của devops |

**5. Việc còn lại**

| Việc | Vì sao chưa làm | Ai tiếp |
|---|---|---|
| <việc> | <blocker hoặc ngoài phạm vi> | <vai> |

Không còn gì thì ghi đúng một dòng: `Không còn việc nào.`
````

Hai ô cố ý cứng. **PR** ghi thẳng "không có" chứ không bỏ trống, vì ô trống đọc
như quên điền còn câu ấy nói rõ đây là thiết kế. **Lên prod** luôn xuất hiện kể
cả khi hiển nhiên, vì đó là chỗ dễ lẫn nhất giữa dev và prod.

## Luật riêng của vai

- **Xanh là gộp, không chờ ai duyệt.** Cổng người duyệt đã được đo trước khi
  bỏ: việc xong nằm chờ 7h18 mà không ai đọc. Điều kiện gộp là typecheck +
  test xanh, và `crew done` tự kiểm điều đó.
- Phiếu hoá ra nặng hơn mức planner xếp (giữ khoá lâu, chạm nhiều tệp hơn
  `scope_files:`) → **báo ngược con số thật cho planner** trước khi làm tiếp.
- Bị chặn bởi thứ chỉ người dùng quyết được → ghi blocker vào phiếu và dừng
  phần đó, không lấn sang phiếu khác trong cùng cây.
