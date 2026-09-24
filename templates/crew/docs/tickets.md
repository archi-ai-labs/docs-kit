# tickets — token, ba mức thi hành, và ngưỡng chẻ phiếu

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
`../<repo>-crew/log.tsv` — đó là cách ngưỡng dưới đây hết dựa trên một điểm
dữ liệu.

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

**Cây của chuỗi không lúc nào rảnh giữa hai phiếu.** Cây đã park là cây rảnh, và
`crew new` của một phiên khác sẽ lấy đúng cây rảnh ấy. Vì vậy `crew done` chuyển
nhánh ngay bên trong lệnh, dưới cùng khoá `assign.lock` mà `crew new` dùng.

Mỗi phiếu chỉ có một phiếu đứng trước, nên chuỗi là một đường thẳng còn chỗ rẽ
nhánh (fork) là một cây. Tại chỗ rẽ, `crew done` đi tiếp vào phiếu có số nhỏ
nhất chưa xong và nêu tên các phiếu còn lại, vì mỗi phiếu ấy cần một phiên
riêng. Phiếu kế tiếp khai `execution: fast-pair` thì chạy ở cây chính, nên cây
executor được park.

Từ 0.41.1, `crew done` tự commit phần đóng sổ (`status: done` và dòng audit) lên
nhánh dev trước khi push. Vì vậy chuỗi chạy liền từ phiếu này sang phiếu kế mà
không ai phải commit tay ở cây chính.

## Chẻ nếu

- `S > 6` (⚠️ số 6 dựa trên đúng một điểm dữ liệu ở repo gốc: trung vị 2–3,
  lớn nhất 10 — coi là chỗ bắt đầu chỉnh, không phải hằng số), **hoặc**
- `C ≥ 3` — đếm số câu "có": đụng schema/API contract/ranh giới component?
  cần tài nguyên khan hiếm? phụ thuộc phiếu khác chưa done? chạm nhiều hơn
  một tầng?, **hoặc**
- chạm nhiều hơn **một tầng kỹ thuật** — câu này đứng riêng vì nó chính là thứ
  cả mô hình tồn tại để tránh: phiếu hai tầng tự kéo hai người vào, dù S nhỏ.

Số đo sinh ra luật chẻ-theo-yêu-cầu: một yêu cầu duy nhất cắt theo tầng đi qua
4 vai mất **15h32** tổng với **~87 phút** có commit; hai phiếu đầu tiên chạy
theo mô hình một-phiếu-một-cây xong trong **15 và 41 phút**.
