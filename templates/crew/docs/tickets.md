# tickets — token, ba mức thi hành, và ngưỡng chẻ phiếu

## Một token cho một phiếu

Số phiếu xuất hiện **nguyên vẹn** ở năm chỗ, nên gõ một con số là tra ra hết:

```
BACKLOG-157        phiếu (docs/23_backlog/)
../<repo>-b157     cây làm việc
work/b157          nhánh
<repo>/b157        tên phiên
BACKLOG-157        chủ khoá (crew lock acquire <resource> 157)
```

## Ba mức thi hành

Lane (STANDARD §5) quyết định đường tài liệu; mức thi hành quyết định chỗ làm.
Ghi mức vào frontmatter phiếu bằng trường tuỳ chọn `execution:`.

| `execution:` | Lane | Nhánh | Cây | Điều kiện vào |
|---|---|---|---|---|
| `fast-pair` | fast | nhánh dev trực tiếp | cây chính | ≤ 1 tệp · revert là xong · không chạm contract |
| `fast` | fast | `work/b<nnn>` | cây riêng | fast lane nhưng lớn hơn mức trên |
| `full` | full | `work/b<nnn>` | cây riêng | full lane (đã có Decision) |

Cả ba mức đều có phiếu — `fast-pair` là *phiếu + nhánh dev*, không phải "bỏ
phiếu cho nhanh". Nó tiết kiệm ~10 giây dựng cây và một lượt gộp, tức phần lớn
đời của một bug một dòng.

**Kỷ luật fast-pair** (vì va chạm là có thật, xem `worktrees.md`): sửa xong
commit ngay trong cùng lượt, không để cây chính bẩn vắt qua lượt khác. Một
fast-pair đang mở chặn mọi `crew done` ở phép kiểm cây-sạch.

**Chi phí dựng cây là một đầu vào của việc xếp mức, không phải phí ngầm.**
`crew new` in thời gian dựng cây và ghi dòng `SETUP` vào log; thời gian đó
lớn hơn phần việc dự kiến thì phiếu xuống `fast-pair`, hoặc gộp nhiều phiếu
nhỏ làm một cho đáng một lần dựng.

## Phiếu tự khai kích thước

Planner khai vào frontmatter:

```yaml
scope_files: 3      # S — số tệp code dự kiến chạm
execution: fast     # fast-pair | fast | full
```

`crew done` ghi lại S khai so với số tệp thật (`git diff --stat`) vào
`../<repo>-crew/log.tsv` — đó là cách ngưỡng dưới đây hết dựa trên một điểm
dữ liệu.

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
