---
description: "Vai executor — một phiếu hoặc một chuỗi phiếu (crew new --chain), mỗi phiếu một nhánh, làm trọn tới done rồi tự gộp."
argument-hint: "<số phiếu, ví dụ: 157>"
disable-model-invocation: true
---

Phiên này đội mũ **executor** cho phiếu `BACKLOG-$ARGUMENTS`
(`.claude/crew/roles.md`).

## Bước 0 — đúng title, trước mọi việc khác

Chạy `scripts/crew new $ARGUMENTS` (bước 1) trước, vì title cần biết bạn ngồi ở
cây nào; rồi `scripts/crew name executor` ngay sau đó. Xanh thì làm tiếp; đỏ thì
đặt lại title rồi chạy lại.

Title gồm các phần lệnh tự đọc từ git và từ phiếu, bạn không truyền gì cả:
`<repo> · executor · b157 · d009 · e1 · processing` — nhánh bạn mở, tài liệu gốc
mà phiếu phục vụ (`source_ref`, ở đây là DECISION-009), cây bạn ngồi, và trạng
thái. Ô gốc là thứ cho người dùng biết phải quay lại planner nào. Phiếu nằm trong
một chuỗi (`after_ref:`) thì title có thêm đoạn `<đầu>→<cuối>` sau ô gốc, ví dụ
`b333 · d009 · 332→336`, và đoạn đó cũng do lệnh tự đọc từ các phiếu. Phiên sinh
ra ở `processing`, **đổi sang `finishing` ngay khi bạn
viết commit mang trailer** (bước 4), rồi **sang `finished` khi `crew done` đã
gộp xong và đóng sổ phiếu** (bước 5). Cứ mỗi lần trạng thái đổi thì chạy lại
lệnh này. Trong app phiên tự đổi title của chính nó được, ngoài
terminal thì đưa dòng `/rename` mà lệnh in ra cho người dùng.

Trong app desktop, vào nhóm sidebar theo mục "Nhóm sidebar" của
`.claude/crew/roles.md`, với lệnh `scripts/crew name executor --group` (phiếu
fast-pair thì kèm số phiếu). Làm lại khi ô gốc trong title đổi, ví dụ khi chuỗi
chuyển sang một phiếu phục vụ tài liệu khác.

Nếu bạn được mở từ một task chứ không do người dùng gõ `/executor`: bạn không
**gọi** được tệp vai này, vì mọi tệp vai đều khoá `disable-model-invocation` —
cái mũ do người giao chứ không phải thứ model tự đội. Lấy nội dung nó bằng
`scripts/crew role executor`, đọc từ cây chính nên chạy được cả khi bạn đang
đứng trong cây của executor.

## Vòng làm việc

1. `scripts/crew new $ARGUMENTS` — phiếu rơi vào executor rảnh trên nhánh
   `work/b$ARGUMENTS`; làm việc TRONG cây mà lệnh in ra. Không còn cây rảnh thì
   lệnh tự dựng thêm một executor, nên bạn không bao giờ bị chặn ở bước này.

   Prompt giao **cả chuỗi** thì ghi sẵn `scripts/crew new <đầu> --chain`; hãy
   chạy đúng dòng đó. Prompt chỉ giao một phiếu thì không có `--chain`, và bạn
   đừng tự thêm, vì cờ này báo cho `crew done` rằng phiên sẽ làm tiếp các phiếu
   sau.

   **Phiếu khai `execution: fast-pair` thì bỏ qua bước 1 này.** Lệnh sẽ từ chối
   và nói lý do: bạn sửa thẳng trên nhánh dev ở cây chính, commit ngay trong
   cùng lượt, không dựng cây và không mở nhánh. Bước 5 cũng bỏ — phiếu fast-pair
   đóng bằng trailer, `crew done` không tham gia. Trailer của nó rơi thẳng lên
   nhánh dev nên title chỉ sang `finished` khi phiếu đã được đóng sổ, tức là
   `status: done` kèm dòng audit.
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

   **Bạn đang mang một chuỗi** khi `crew done` in ra dòng `stays busy: the chain
   goes on with BACKLOG-<kế>`. Lúc đó lệnh đã chuyển cây của bạn thẳng sang nhánh
   `work/b<kế>`, cắt từ nhánh dev vừa nhận phiếu này, và cây chưa hề rảnh lúc
   nào. Đừng chạy `crew new <kế>`, vì cây đã giữ phiếu đó rồi. Giữa chuỗi bạn
   **không** viết báo cáo cuối; thay vào đó viết đúng một dòng tiến độ, chép từ
   dòng `chain    :` mà lệnh vừa in, kèm sha của phiếu vừa gộp:

   ```
   Tiến độ 332→334: landed 332 · e1 on 333 · queued 334 — vừa gộp 332 @ 58271d6
   ```

   Sau đó chạy `scripts/crew name executor` không kèm số, rồi quay lại bước 2 với
   phiếu kế. Từ đây mọi bước dùng số của phiếu cây đang giữ chứ không dùng
   `$ARGUMENTS`. Muốn dừng chuỗi sau phiếu đang làm thì thay lệnh ở bước 5 bằng
   `scripts/crew done <số phiếu> --park`: cây được thả, và `crew status` chỉ ra
   phiếu nào đang chờ người mang tiếp.

   **`crew done` in `[done:alone]`** nghĩa là phiếu kế trong chuỗi đã sẵn sàng
   nhưng phiếu này được mở không có `--chain`, nên cây đã được thả. Nếu prompt
   chỉ giao phiếu này thì bạn dừng ở đây, vì đó đúng là việc được giao. Nếu
   prompt giao cả chuỗi (tức planner quên `--chain`) thì chạy lệnh
   `scripts/crew new <kế> --chain` mà dòng đó in ra, từ trong chính cây vừa thả,
   rồi làm tiếp.

   `crew done` tự commit phần đóng sổ (`status: done` và dòng audit) lên nhánh
   dev, nên bạn không phải commit gì ở cây chính. Nếu lệnh in dòng
   `[done:closeout]` thì commit ấy chưa thành, thường vì pre-commit hook của repo
   từ chối. Lệnh nêu đích danh các tệp; hãy commit chúng ở cây chính trước
   `crew done` kế tiếp, vì kiểm 2 sẽ chặn nếu chúng còn nằm đó.

5b. `scripts/crew name executor $ARGUMENTS` lần cuối, **sau phiếu cuối cùng của
   chuỗi**, hoặc sau phiếu duy nhất nếu bạn không mang chuỗi. Lần này bạn phải truyền
   số phiếu, vì `crew done` đã park cây nên nhánh không còn ở đó để lệnh tự đọc
   ra. Trạng thái bây giờ là `finished`, nghĩa là phiếu không còn việc gì và
   bạn đóng phiên được. Nếu lệnh báo `[name:unclosed]` thì phần gộp đã xong
   nhưng phiếu chưa đóng sổ, vì vậy hãy chạy `/docs-kit:docs-sync` rồi thử lại.

6. **Báo cáo cuối** theo mẫu dưới đây, đúng năm mục và đúng thứ tự ấy. Đây là
   thứ duy nhất người giao việc đọc được mà không phải mở repo. Phiên mang chuỗi
   viết **một** báo cáo cho cả chuỗi, sau `crew done` cuối cùng (phiếu cuối,
   `--park`, hoặc lúc dừng vì blocker), theo **mẫu cho chuỗi** ở cuối tệp.

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

## Mẫu báo cáo cuối cho chuỗi

Người giao việc đọc báo cáo này để biết chuỗi đi tới đâu, nên mục 0 đứng trước
năm mục quen thuộc. Mục 0 chép từ khối `carried  :` mà `crew done` cuối cùng
in ra, chứ không gõ lại theo trí nhớ. Mỗi dòng của khối ấy là một phiếu phiên đã
mang, kèm sha đóng phiếu trên nhánh dev, `declared=`/`actual=` và trạng thái.
Dòng `not carried yet:` (nếu có) là phiếu chuỗi còn lại cùng lệnh để phiên khác
mang tiếp.

````
## Chuỗi BACKLOG-<đầu> → BACKLOG-<cuối> — <một câu việc cả chuỗi đã làm>

**0. Chuỗi**

| Phiếu | Việc | Commit | Phạm vi | Trạng thái |
|---|---|---|---|---|
| BACKLOG-<đầu> | <một câu> | [`<sha ngắn>`](<base>/commit/<sha>) | khai `<S>` · thật `<N>` | done |
| BACKLOG-<kế> | <một câu> | [`<sha ngắn>`](<base>/commit/<sha>) | khai `<S>` · thật `<N>` | done |
| BACKLOG-<cuối> | — | — | — | chưa làm: <lý do dừng> |

Cây: `<e<k>>` đã được thả sau phiếu cuối.
— hoặc —
Chuỗi dừng ở BACKLOG-<nnn> vì <lý do>. Phiếu kế cần một phiên mới: `<lệnh ở dòng not carried yet>`.

**1. Việc đã làm** — bảng như mẫu thường, thêm cột `Phiếu` ở đầu.

**2. Luồng đổi thế nào** — một cặp `trước`/`sau` cho cả chuỗi: `trước` là lúc
chưa có phiếu đầu, `sau` là lúc phiếu cuối đã gộp.

**3. Bằng chứng** — chỉ còn dòng Kiểm thử và Khoá, vì Commit và Phạm vi đã nằm
ở mục 0.

**4. Git** — ô Nhánh liệt kê mọi `work/b<nnn>` của chuỗi; ô Gộp vào là nhánh
dev @ sha close-out của phiếu cuối đã gộp. Hai ô PR và Lên prod giữ nguyên.

**5. Việc còn lại** — như mẫu thường, và gồm cả các phiếu chuỗi chưa làm.
````

Một chuỗi dừng giữa chừng vẫn là một báo cáo hợp lệ. Điều duy nhất không được
thiếu là câu `Cây:`/`Chuỗi dừng ở`, vì chỉ câu đó cho người đọc biết phiếu kế
đang có người làm hay đang chờ.

## Luật riêng của vai

- **Xanh là gộp, không chờ ai duyệt.** Cổng người duyệt đã được đo trước khi
  bỏ: việc xong nằm chờ 7h18 mà không ai đọc. Điều kiện gộp là typecheck +
  test xanh, và `crew done` tự kiểm điều đó.
- Phiếu hoá ra nặng hơn mức planner xếp (giữ khoá lâu, chạm nhiều tệp hơn
  `scope_files:`) → **báo ngược con số thật cho planner** trước khi làm tiếp.
- Bị chặn bởi thứ chỉ người dùng quyết được → ghi blocker vào phiếu và dừng
  phần đó, không lấn sang phiếu khác trong cùng cây.
