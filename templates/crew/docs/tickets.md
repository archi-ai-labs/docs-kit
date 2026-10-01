# tickets — token, ba mức thi hành, và luật chẻ phiếu

## Một token cho một phiếu

Số phiếu xuất hiện **nguyên vẹn** ở bốn chỗ; chỉ cái cây là dùng lại qua nhiều
phiếu nên nó mang địa chỉ executor:

```
BACKLOG-157                                 phiếu (docs/23_backlog/)
work/b157                                   nhánh
BACKLOG-157                                 chủ khoá (crew lock acquire … 157)
<repo> · executor · b157 · d009 · e1 · …    tên phiên (d009 là gốc, đọc từ source_ref;
                                            fast-pair thì e1 → main; phiếu trong
                                            chuỗi thêm đoạn 157→160 trước e1)
../<repo>-e1                                cây của executor (dùng lại)
```

Nối hai địa chỉ ấy là **nhánh mà executor đang checkout**: e1 đang mở
`work/b157` tức e1 đang giữ BACKLOG-157, và e1 ở HEAD tách rời tức e1 đang rảnh.

## Ba mức thi hành

Lane (STANDARD §5) quyết định đường tài liệu; mức thi hành quyết định chỗ làm.
Ghi mức vào frontmatter phiếu bằng trường tuỳ chọn `execution:`.

| `execution:` | Lane | Nhánh | Cây | Điều kiện vào |
|---|---|---|---|---|
| `fast-pair` | fast | nhánh dev trực tiếp | cây chính | ≤ 1 tệp · revert là xong · không chạm contract |
| `fast` | fast | `work/b<nnn>` | một executor rảnh | fast lane nhưng lớn hơn mức trên |
| `full` | full | `work/b<nnn>` | một executor rảnh | full lane (đã có Decision) |

Cả ba mức đều có phiếu — `fast-pair` là *phiếu + nhánh dev*, không phải "bỏ
phiếu cho nhanh". Nó tiết kiệm một lượt gộp và một chỗ trong pool, tức phần lớn
đời của một bug một dòng.

**Kỷ luật fast-pair** (vì va chạm là có thật, xem `worktrees.md`): sửa xong
commit ngay trong cùng lượt, không để cây chính bẩn vắt qua lượt khác. Một
fast-pair đang mở chặn mọi `crew done` ở phép kiểm cây-sạch.

**Pool tự lớn theo nhu cầu, nên thứ cần canh là lúc thu hẹp lại.** `crew new`
không còn executor rảnh thì tự dựng thêm và ghi dòng `GROW`; `crew status` cho
biết pool đang bao nhiêu và có vượt trần đọc chưa. Hết đợt việc dồn thì gỡ bớt
bằng `scripts/crew executor rm <k>`.

## Việc không thành phiếu

Phiếu là đơn vị giao việc, không phải sổ ghi mọi thứ cần làm. Giá một phiếu là
một nhánh, một lượt gộp và một chỗ trong pool suốt thời gian nó chạy, nên việc
rẻ hơn cái giá ấy thì làm tại chỗ.

Không thành phiếu: dọn dẹp tài liệu layer 2 (archive hoặc đóng một Issue, sửa
trạng thái, sửa typo trong phiếu). Người phát hiện làm ngay kèm dòng audit,
hoặc nó đi kèm phiếu đã sinh ra nó.

Có thành phiếu: mọi thứ chạm code, kể cả một dòng — nhưng khi đó nó là
`fast-pair` ở bảng dưới, không phải một cây riêng.

## Phiếu tự khai kích thước

Planner khai vào frontmatter:

```yaml
scope_files: 3      # S — số tệp code dự kiến chạm
execution: fast     # fast-pair | fast | full
```

`crew done` ghi lại S khai so với số tệp thật (`git diff --stat`) vào
`../<repo>-crew/log.tsv`. Hai số này cho biết planner ước lượng đúng tới đâu,
còn việc có chẻ phiếu hay không thì theo mục «Chẻ phiếu theo độ khó» bên dưới.

## Chuỗi phiếu — `after_ref:`

Chuỗi (chain) là những phiếu không chạy song song được, vì phiếu sau sửa chính
thứ mà phiếu trước dựng ra. Planner ghi thứ tự vào **phiếu sau**:

```yaml
id: BACKLOG-333
after_ref: BACKLOG-332   # 333 chỉ bắt đầu khi 332 đã gộp vào nhánh dev
```

Một phiên executor mang trọn một chuỗi khi nó mở phiếu đầu bằng
`scripts/crew new 332 --chain`. Thứ tự chuỗi do planner ghi trong phiếu, còn
việc phiên nào mang chuỗi do prompt quyết định, nên cờ `--chain` chỉ nằm trong
prompt chuỗi. Phiếu không ai xâu vào chuỗi là chuỗi một phần tử, nên nó vẫn đi
một phiên như trước. Title luôn chỉ đúng một phiếu,
là phiếu cây đang giữ, và thêm đoạn `<đầu>→<cuối>` sau ô gốc để biết phiếu
thuộc chuỗi nào:

```
<repo> · executor · b333 · d009 · 332→336 · e1 · processing
```

| Lệnh | Chuỗi đổi gì |
|---|---|
| `crew new 332 --chain` | phiên này mang chuỗi từ 332 trở đi; cờ được ghi vào dòng `NEW` của `log.tsv` và tự truyền qua mỗi lần chuyển cây |
| `crew new 333` | từ chối với `[new:after]` khi 332 chưa gộp vào nhánh dev, và nói executor đang giữ 332 có mang chuỗi hay không |
| `crew done 332` | phiên mang chuỗi: chuyển cây thẳng từ `work/b332` sang `work/b333` mà không park ở giữa, rồi in một dòng tiến độ; thêm `--park` thì chuỗi dừng tại đây. Phiên mở 332 không có `--chain`: cây được thả kèm `[done:alone]` và lệnh `scripts/crew new 333 --chain` cho phiên kế |
| `crew done` cuối của chuỗi | in khối `carried  :` gồm các phiếu phiên đã mang, sha đóng từng phiếu và cỡ đã ghi, làm nguồn cho báo cáo cuối |
| `crew status` | khối `chains:` cho biết phiếu nào đã gộp, executor nào giữ phiếu nào (thêm `(this ticket only)` khi phiên đó không mang chuỗi), phiếu nào đang chờ |
| `crew wait 332` | chặn cho tới khi 332 đã gộp vào nhánh dev (cùng phép thử mà `crew new` dùng) và không cây nào còn giữ `work/b332`, rồi in từng phiếu có `after_ref` trỏ về 332: cây mà phiên mang chuỗi đã nhận nó, hoặc lệnh để mở nó. Nhận nhiều số thì chờ đủ tất cả |

**Cây của chuỗi không lúc nào rảnh giữa hai phiếu.** Cây đã park là cây rảnh, và
`crew new` của một phiên khác sẽ lấy đúng cây rảnh ấy. Vì vậy `crew done` chuyển
nhánh ngay bên trong lệnh, dưới cùng khoá `assign.lock` mà `crew new` dùng.

Mỗi phiếu chỉ có một phiếu đứng trước, nên chuỗi là một đường thẳng còn chỗ rẽ
nhánh (fork) là một cây. Tại chỗ rẽ, `crew done` đi tiếp vào phiếu có số nhỏ
nhất chưa xong và nêu tên các phiếu còn lại, vì mỗi phiếu ấy cần một phiên
riêng. Phiếu kế tiếp khai `execution: fast-pair` thì chạy ở cây chính, nên cây
executor được park.

Các phiếu còn lại ở chỗ rẽ chỉ mở được khi phiếu đứng trước đã gộp. Để biết lúc
đó, planner chạy `scripts/crew wait <phiếu trước>` ở chế độ nền (background) rồi
mở phiên cho từng phiếu theo lệnh mà nó in ra. Lệnh này chờ thêm cả khoảng giữa
lúc closer vào nhánh dev và lúc `crew done` chuyển cây, vì nếu thoát sớm hơn thì
nó sẽ báo phiếu kế là sẵn sàng trong khi phiên mang chuỗi sắp nhận chính phiếu đó.

**Phiếu có nhiều phiếu đứng trước (join) thì để trống `after_ref`.** Trường này
chỉ chứa một số. Nếu trỏ nó vào một chuỗi thì `crew new` chỉ chặn theo chuỗi đó,
còn phiên mang chuỗi ấy sẽ được `crew done` chuyển thẳng sang phiếu join trong
khi các chuỗi kia vẫn đang chạy. Cách đúng là chạy
`scripts/crew wait <phiếu cuối của mỗi chuỗi>…` ở chế độ nền, và mở phiếu join khi
lệnh thoát.

Từ 0.41.1, `crew done` tự commit phần đóng sổ (`status: done` và dòng audit) lên
nhánh dev trước khi push. Vì vậy chuỗi chạy liền từ phiếu này sang phiếu kế mà
không ai phải commit tay ở cây chính.

## Chẻ phiếu theo độ khó

Một phiếu ôm trọn một yêu cầu. Planner chỉ chẻ khi việc khó, và không bao giờ
chẻ chỉ vì phiếu chạm nhiều tệp.

Số đo đứng sau luật này lấy từ 421 phiếu của một repo crew có bốn kho con, đo
tháng 9/2026. Điểm chuẩn là **18 trên 100 phiếu gặp trục trặc**, tức phải làm
lại sau khi đã báo xong, bị dừng giữa chừng để hỏi, hoặc phải mở phiếu khác để
sửa tiếp. Phiếu ≤ 6 tệp gặp trục trặc 19 và phiếu > 6 tệp gặp 17, nên số tệp
không báo trước được gì; luật cũ «`S > 6` thì chẻ» vì vậy đã bị bỏ.

### Chấm điểm lúc cắt

Planner trả lời bốn câu trước khi viết phiếu. Cả bốn đều biết được trước khi
làm, và đều không phụ thuộc repo làm gì.

| Câu hỏi | Điểm |
|---|---|
| Phiếu chạm thêm bao nhiêu tầng kỹ thuật ngoài tầng đầu tiên (giao diện, API, worker, phần cứng… theo cách repo chia)? | 1 mỗi tầng thêm, tối đa 2 |
| Phiếu có đổi hợp đồng không: API, schema CSDL, kiểu dữ liệu mà nhiều thành phần cùng dùng? | 1 |
| Phiếu có cần Decision không (`execution: full`)? | 1 |
| Phiếu có cần khoá một tài nguyên khai trong `crew.resources` không? | 1 |

Planner ghi điểm vào thân phiếu thành một dòng như `Độ khó: 2 (tầng +1, hợp
đồng)`, để lần đo sau đối chiếu được điểm đoán với kết quả thật.

### Chia theo mức

| Điểm | Mức | Cách chia | Trục trặc / 100 (chuẩn 18) |
|---|---|---|---|
| 0–1 | Dễ | Mỗi kho một phiếu cho một yêu cầu, bao nhiêu tệp cũng được. Việc cơ học lặp lại như dời tệp, cắt chú thích hay đổi chữ cũng giữ một phiếu mỗi kho. | 13 |
| 2 | Vừa | Một yêu cầu là một phiếu. Chỉ tách theo kho khi kho sau phải chờ kho trước phát hành gói, và khi đó phiếu sau khai `after_ref`. | 22 |
| ≥ 3 | Khó | Tách những lát tách được: lát đổi hợp đồng đứng trước lát dùng nó, lần chạy trên tài nguyên thật là một lát riêng, việc dời dữ liệu đi theo thứ tự mở rộng → dời → thu hẹp (expand → migrate → contract). Mỗi lát có «Xong khi» riêng và nối bằng `after_ref`. Không tách được thì ghi lý do vào phiếu. | 34 |

Việc dễ bị chẻ nhỏ là chỗ tốn nhất đã đo được. Trong repo đo, 28 việc chủ yếu
dễ bị chẻ thành 187 phiếu và 188 PR, trong khi mỗi kho một phiếu chỉ cần 48.
Cùng một việc dọn chú thích, kho làm một phiếu xong 69 tệp trong 0,9 giờ với một
lượt gộp, còn kho bị chẻ mười một phiếu mất 11,1 giờ cho 315 tệp và bảy lượt gộp.

Chủ repo có thể ra lệnh chẻ để chạy song song cho nhanh, và lệnh đó thắng luật
này. Khi ấy planner chép nguyên văn lệnh vào phiếu, và câu kiểm 3 bên dưới vẫn
áp dụng.

### Năm câu kiểm trước khi cắt từ hai phiếu trở lên

1. **Ranh giới.** Mỗi phiếu là một lát của yêu cầu, không phải một tầng hay
   một nhóm tệp.
2. **Độc lập.** Phiếu nào cần phiếu khác gộp trước thì khai `after_ref`. Dòng
   chữ «chờ phiếu kia» trong thân phiếu không có lệnh nào đọc: repo đo có 145
   cặp phụ thuộc mà chỉ 1 cặp được khai.
3. **Chồng tệp.** Hai phiếu cùng kho sửa chung một tệp mã thì gộp làm một hoặc
   nối chuỗi. Hai phiếu cùng kho chạm một dòng mà PR nào cũng sửa (hằng số đếm
   test, số phiên bản schema, snapshot) thì gộp tuần tự, không mở PR song song.
4. **Kiểm được.** Mỗi phiếu có «Xong khi» chạy được khi chỉ riêng phiếu đó đã
   gộp.
5. **Cân đối.** Phiếu ≤ 2 tệp hoặc ≤ 10 dòng thì nhập vào phiếu anh em, trừ
   `fast-pair`.

Va chạm khi gộp thì gỡ ngay trong PR gộp sau, không cắt phiếu mới chỉ để gỡ va.

Luật một-phiếu-một-yêu-cầu còn có số đo gốc: một yêu cầu duy nhất cắt theo tầng
đi qua 4 vai mất **15h32** tổng với **~87 phút** có commit, trong khi hai phiếu
đầu tiên chạy theo mô hình một-phiếu-một-cây xong trong **15 và 41 phút**.

Các mốc 0–1 · 2 · ≥ 3 được đo trên một repo. Repo khác đo lại sau một tháng
chạy, và chỉ dời mốc khi chủ repo duyệt kèm số đo đó.
